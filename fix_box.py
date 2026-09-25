"""Clip YOLO boxes that stick out of the image to the image boundaries.

Usage:
    python fix_box.py [--labels DIR] [--dry-run] [--max-clip 0.02]

- Small overshoots (up to --max-clip, as a share of the image side) are clipped.
- Boxes that are completely outside the image are removed.
- Large overshoots are NOT changed: they are most likely annotation mistakes
  and are listed for manual review.
- All other lines in a file are kept exactly as they are.

Exit code: 0 = nothing left to review, 1 = some boxes need manual review.
"""

import argparse
import sys
from pathlib import Path

from common import (
    EPS,
    PROJECT_DIR,
    format_label_line,
    list_labels,
    parse_label_line,
    require_dir,
    to_corners,
    write_text_atomic,
)

DEFAULT_MAX_CLIP = 0.02


def fix_file(label_path, max_clip):
    """Return (new_text or None, clipped, removed, review_messages)."""
    lines = label_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    clipped = 0
    removed = 0
    review = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            new_lines.append(line)
            continue

        try:
            class_id, box = parse_label_line(line)
        except ValueError:
            new_lines.append(line)  # validate.py reports malformed lines
            continue

        if box[2] <= 0 or box[3] <= 0:
            new_lines.append(line)  # validate.py reports invalid sizes
            continue

        x1, y1, x2, y2 = to_corners(box)
        overshoot = max(-x1, -y1, x2 - 1, y2 - 1)

        if overshoot <= EPS:
            new_lines.append(line)
            continue

        cx1, cy1, cx2, cy2 = (min(1.0, max(0.0, v)) for v in (x1, y1, x2, y2))
        new_w = cx2 - cx1
        new_h = cy2 - cy1

        if new_w <= EPS or new_h <= EPS:
            removed += 1
            continue  # the box is completely outside the image: drop it

        if overshoot > max_clip:
            review.append(
                f"{label_path.name}:{line_number}: box sticks out by "
                f"{overshoot:.3f} of the image size (> {max_clip}); check manually"
            )
            new_lines.append(line)
            continue

        new_box = ((cx1 + cx2) / 2, (cy1 + cy2) / 2, new_w, new_h)
        new_lines.append(format_label_line(class_id, new_box))
        clipped += 1

    if not clipped and not removed:
        return None, 0, 0, review

    text = "\n".join(new_lines) + ("\n" if new_lines else "")
    return text, clipped, removed, review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--labels", type=Path, default=PROJECT_DIR / "labels",
                        help="folder with YOLO .txt labels (default: ./labels)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would change without modifying files")
    parser.add_argument("--max-clip", type=float, default=DEFAULT_MAX_CLIP,
                        help=f"largest overshoot (share of the image) that is "
                             f"clipped automatically (default: {DEFAULT_MAX_CLIP})")
    args = parser.parse_args()

    try:
        require_dir(args.labels, "Label")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 2

    files_changed = 0
    boxes_clipped = 0
    boxes_removed = 0
    review_all = []

    for label_path in list_labels(args.labels):
        try:
            text, clipped, removed, review = fix_file(label_path, args.max_clip)
        except (OSError, UnicodeDecodeError) as e:
            print(f"ERROR: cannot read {label_path.name}: {e}")
            continue

        review_all.extend(review)
        if text is None:
            continue

        files_changed += 1
        boxes_clipped += clipped
        boxes_removed += removed
        print(f"{'Would fix' if args.dry_run else 'Fixed'}: {label_path.name} "
              f"(clipped: {clipped}, removed: {removed})")
        if not args.dry_run:
            write_text_atomic(label_path, text)

    print()
    print("=" * 50)
    print("BBOX FIX RESULT" + (" (dry run)" if args.dry_run else ""))
    print("=" * 50)
    print(f"Files modified:                {files_changed}")
    print(f"Boxes clipped:                 {boxes_clipped}")
    print(f"Boxes removed (fully outside): {boxes_removed}")
    print(f"Boxes to review manually:      {len(review_all)}")
    for message in review_all:
        print(f"  - {message}")
    print("=" * 50)

    return 1 if review_all else 0


if __name__ == "__main__":
    sys.exit(main())
