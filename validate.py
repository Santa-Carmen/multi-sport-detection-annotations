"""Validate the dataset: images, YOLO label files and their consistency.

Usage:
    python validate.py [--images DIR] [--labels DIR] [--classes FILE] [--strict]

Exit code: 0 = no errors, 1 = errors found (or warnings with --strict),
2 = folders/classes file could not be read.
"""

import argparse
import sys
from collections import Counter, defaultdict

from PIL import Image

from common import (
    BALL_CLASS_NAME,
    DUPLICATE_IOU_THRESHOLD,
    EPS,
    IGNORE_CLASS_NAME,
    IMAGE_EXTENSIONS,
    add_path_args,
    find_duplicates,
    list_images,
    list_labels,
    load_classes,
    parse_label_line,
    require_dir,
    to_corners,
)

# Guidelines, section 7: objects smaller than ~8x8 px are not labeled.
MIN_BOX_PIXELS = 8

# Heuristic: a ball wider/taller than this share of the image is suspicious.
BALL_MAX_SIDE = 0.25


def validate_dataset(image_dir, label_dir, classes):
    errors = []
    warnings = []
    class_counts = Counter()
    total_annotations = 0
    images_without_objects = 0

    ignore_ids = {i for i, n in classes.items() if n == IGNORE_CLASS_NAME}
    ball_ids = {i for i, n in classes.items() if n == BALL_CLASS_NAME}

    images = list_images(image_dir)
    labels = list_labels(label_dir)

    # Files in the images folder that will never be checked.
    for path in sorted(image_dir.iterdir()):
        if (path.is_file() and not path.name.startswith(".")
                and path.suffix.lower() not in IMAGE_EXTENSIONS):
            warnings.append(f"{path.name}: unsupported file in images folder (skipped)")

    # Two images with the same base name would share one label file.
    by_stem = defaultdict(list)
    for image_path in images:
        by_stem[image_path.stem].append(image_path.name)
    for names in by_stem.values():
        if len(names) > 1:
            errors.append(
                "images share the same base name and would use the same label file: "
                + ", ".join(names)
            )

    # Labels without an image.
    image_stems = {p.stem for p in images}
    for label_path in labels:
        if label_path.stem not in image_stems:
            warnings.append(f"{label_path.name}: label file has no matching image")

    for image_path in images:
        # ---- image ----
        try:
            with Image.open(image_path) as img:
                image_width, image_height = img.size
        except Exception as e:
            errors.append(f"{image_path.name}: cannot open image ({e})")
            continue

        if image_width <= 0 or image_height <= 0:
            errors.append(f"{image_path.name}: invalid image dimensions")
            continue

        # ---- label file ----
        label_path = label_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            errors.append(f"{image_path.name}: annotation file is missing")
            continue

        try:
            lines = label_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"{label_path.name}: cannot read annotation ({e})")
            continue

        entries = []  # (line_number, class_id, box) of valid boxes

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            where = f"{label_path.name}:{line_number}"

            try:
                class_id, box = parse_label_line(line)
            except ValueError as e:
                errors.append(f"{where}: {e}")
                continue

            total_annotations += 1

            if class_id not in classes:
                errors.append(f"{where}: unknown class ID {class_id}")
                continue

            x_center, y_center, width, height = box
            line_ok = True

            for name, value in (
                ("x_center", x_center), ("y_center", y_center),
                ("width", width), ("height", height),
            ):
                if not -EPS <= value <= 1 + EPS:
                    errors.append(f"{where}: {name}={value} outside [0, 1]")
                    line_ok = False

            if width <= 0 or height <= 0:
                errors.append(f"{where}: bbox has zero or negative size")
                continue

            if line_ok:
                x1, y1, x2, y2 = to_corners(box)
                if x1 < -EPS or y1 < -EPS or x2 > 1 + EPS or y2 > 1 + EPS:
                    errors.append(f"{where}: bbox goes outside image")
                    line_ok = False

            if not line_ok:
                continue

            class_name = classes[class_id]
            class_counts[class_name] += 1

            # Size checks (heuristics -> warnings). `ignore` regions may be tiny.
            if class_id not in ignore_ids:
                w_px = width * image_width
                h_px = height * image_height
                if w_px < MIN_BOX_PIXELS or h_px < MIN_BOX_PIXELS:
                    warnings.append(
                        f"{where}: {class_name} box is {w_px:.1f}x{h_px:.1f} px "
                        f"(smaller than {MIN_BOX_PIXELS} px)"
                    )
            if class_id in ball_ids and (width > BALL_MAX_SIDE or height > BALL_MAX_SIDE):
                warnings.append(
                    f"{where}: ball box is very large "
                    f"({width:.2f}x{height:.2f} of the image)"
                )

            entries.append((line_number, class_id, box))

        if not entries:
            images_without_objects += 1

        # ---- duplicates ----
        for kept_line, dup_line, class_id, iou in find_duplicates(entries):
            warnings.append(
                f"{label_path.name}: duplicate annotations at lines "
                f"{kept_line} and {dup_line} "
                f"(class={classes[class_id]}, IoU={iou:.3f})"
            )

    return {
        "images": len(images),
        "annotations": total_annotations,
        "class_counts": class_counts,
        "images_without_objects": images_without_objects,
        "errors": errors,
        "warnings": warnings,
    }


def print_report(result, classes):
    errors = result["errors"]
    warnings = result["warnings"]

    print("=" * 60)
    print("DATASET VALIDATION")
    print("=" * 60)
    print(f"Images checked:          {result['images']}")
    print(f"Annotations checked:     {result['annotations']}")
    print(f"Images without objects:  {result['images_without_objects']}")
    print("Boxes per class:")
    for name in classes.values():
        print(f"  {name:<10} {result['class_counts'].get(name, 0)}")
    print(f"Errors:                  {len(errors)}")
    print(f"Warnings:                {len(warnings)}")

    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("\n✓ Dataset passed validation!")
    elif not errors:
        print("\n✓ No critical errors found. Review the warnings.")
    else:
        print("\n✗ Dataset contains errors. Review the report above.")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_path_args(parser)
    parser.add_argument(
        "--strict", action="store_true",
        help="exit with code 1 if there are warnings too",
    )
    args = parser.parse_args()

    try:
        require_dir(args.images, "Image")
        require_dir(args.labels, "Label")
        classes = load_classes(args.classes)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 2

    if not list_images(args.images):
        print("ERROR: No images found.")
        return 2

    result = validate_dataset(args.images, args.labels, classes)
    print_report(result, classes)

    if result["errors"] or (args.strict and result["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
