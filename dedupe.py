"""Remove duplicate YOLO boxes (same class, IoU above a threshold).

Usage:
    python dedupe.py [--labels DIR] [--threshold 0.95] [--dry-run]

The first box of a duplicate group is kept, later ones are removed.
All other lines in a file are kept exactly as they are.
"""

import argparse
import sys
from pathlib import Path

from common import (
    DUPLICATE_IOU_THRESHOLD,
    PROJECT_DIR,
    find_duplicates,
    list_labels,
    parse_label_line,
    require_dir,
    write_text_atomic,
)


def dedupe_file(label_path, threshold):
    """Return (new_text or None, [(kept_line, removed_line, class_id, iou)])."""
    lines = label_path.read_text(encoding="utf-8").splitlines()

    entries = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            class_id, box = parse_label_line(line)
        except ValueError:
            continue  # validate.py reports malformed lines
        if box[2] <= 0 or box[3] <= 0:
            continue
        entries.append((line_number, class_id, box))

    duplicates = find_duplicates(entries, threshold)
    if not duplicates:
        return None, []

    drop = {dup_line for _, dup_line, _, _ in duplicates}
    new_lines = [l for i, l in enumerate(lines, start=1) if i not in drop]
    text = "\n".join(new_lines) + ("\n" if new_lines else "")
    return text, duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--labels", type=Path, default=PROJECT_DIR / "labels",
                        help="folder with YOLO .txt labels (default: ./labels)")
    parser.add_argument("--threshold", type=float, default=DUPLICATE_IOU_THRESHOLD,
                        help=f"IoU above which boxes are duplicates "
                             f"(default: {DUPLICATE_IOU_THRESHOLD})")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be removed without modifying files")
    args = parser.parse_args()

    try:
        require_dir(args.labels, "Label")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 2

    files_changed = 0
    boxes_removed = 0

    for label_path in list_labels(args.labels):
        try:
            text, duplicates = dedupe_file(label_path, args.threshold)
        except (OSError, UnicodeDecodeError) as e:
            print(f"ERROR: cannot read {label_path.name}: {e}")
            continue

        if text is None:
            continue

        files_changed += 1
        boxes_removed += len(duplicates)
        for kept, removed, class_id, iou in duplicates:
            print(f"{label_path.name}: line {removed} duplicates line {kept} "
                  f"(class {class_id}, IoU={iou:.3f})")
        if not args.dry_run:
            write_text_atomic(label_path, text)

    print()
    print("=" * 50)
    print("DEDUPLICATION RESULT" + (" (dry run)" if args.dry_run else ""))
    print("=" * 50)
    print(f"Files modified:  {files_changed}")
    print(f"Boxes removed:   {boxes_removed}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
