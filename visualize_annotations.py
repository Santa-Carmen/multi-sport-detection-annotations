"""Draw YOLO annotations on their matching images for visual review."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from common import add_path_args, list_images, load_classes, parse_label_line, require_dir


# The palette repeats for projects with more classes than the colours below.
COLORS = (
    (230, 57, 70),    # red
    (29, 185, 84),    # green
    (0, 123, 255),    # blue
    (255, 159, 28),   # orange
    (142, 68, 173),   # purple
    (0, 172, 193),    # turquoise
)


def output_path(output_dir: Path, image_path: Path) -> Path:
    """Use PNG for formats Pillow cannot reliably save after drawing."""
    if image_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return output_dir / image_path.name
    return output_dir / f"{image_path.stem}.png"


def draw_box(draw: ImageDraw.ImageDraw, box, image_size, color, label: str) -> None:
    """Convert a normalized YOLO box to pixels and draw it with a class label."""
    x_center, y_center, width, height = box
    image_width, image_height = image_size
    left = round((x_center - width / 2) * image_width)
    top = round((y_center - height / 2) * image_height)
    right = round((x_center + width / 2) * image_width)
    bottom = round((y_center + height / 2) * image_height)

    line_width = max(2, round(min(image_size) / 400))
    draw.rectangle((left, top, right, bottom), outline=color, width=line_width)
    text_box = draw.textbbox((left, top), label)
    text_width = text_box[2] - text_box[0] + 6
    text_height = text_box[3] - text_box[1] + 4
    text_top = top - text_height if top >= text_height else top
    draw.rectangle((left, text_top, left + text_width, text_top + text_height), fill=color)
    draw.text((left + 3, text_top + 2), label, fill="white")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draw colored bounding boxes from YOLO labels onto images."
    )
    add_path_args(parser)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parent / "annotated_images",
        help="folder for annotated copies (default: ./annotated_images)",
    )
    args = parser.parse_args()

    require_dir(args.images, "Images")
    require_dir(args.labels, "Labels")
    classes = load_classes(args.classes)
    args.output.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0
    for image_path in list_images(args.images):
        label_path = args.labels / f"{image_path.stem}.txt"
        if not label_path.is_file():
            print(f"SKIP {image_path.name}: no matching label file")
            skipped += 1
            continue

        try:
            with Image.open(image_path) as source:
                image = source.convert("RGB")
        except OSError as error:
            print(f"SKIP {image_path.name}: cannot open image ({error})")
            skipped += 1
            continue

        draw = ImageDraw.Draw(image)
        for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                class_id, box = parse_label_line(line)
            except ValueError as error:
                print(f"WARNING {label_path.name}:{line_number}: {error}; skipped")
                continue
            if class_id not in classes:
                print(f"WARNING {label_path.name}:{line_number}: unknown class ID {class_id}; skipped")
                continue

            draw_box(draw, box, image.size, COLORS[class_id % len(COLORS)], classes[class_id])

        destination = output_path(args.output, image_path)
        try:
            image.save(destination, quality=95)
        except OSError as error:
            print(f"SKIP {image_path.name}: cannot save output ({error})")
            skipped += 1
            continue
        print(f"SAVED {destination}")
        saved += 1

    print(f"Done: {saved} image(s) saved, {skipped} image(s) skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
