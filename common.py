"""Shared helpers for the dataset utility scripts (YOLO labels)."""

import argparse
import math
import os
import shutil
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Tolerance for floating-point errors when comparing coordinates with 0 and 1.
EPS = 1e-6

# Two boxes of the same class with IoU above this value are duplicates.
DUPLICATE_IOU_THRESHOLD = 0.95

PLAYER_CLASS_NAME = "player"
BALL_CLASS_NAME = "ball"
IGNORE_CLASS_NAME = "ignore"


def add_path_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add --images / --labels / --classes options (default: next to the scripts)."""
    parser.add_argument(
        "--images", type=Path, default=PROJECT_DIR / "images",
        help="folder with images (default: ./images)",
    )
    parser.add_argument(
        "--labels", type=Path, default=PROJECT_DIR / "labels",
        help="folder with YOLO .txt labels (default: ./labels)",
    )
    parser.add_argument(
        "--classes", type=Path, default=PROJECT_DIR / "classes.txt",
        help="file with class names, one per line (default: ./classes.txt)",
    )
    return parser


def load_classes(path: Path) -> dict:
    """Read classes.txt. The line number (from 0) is the class ID."""
    if not path.is_file():
        raise FileNotFoundError(f"Classes file not found: {path}")
    names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    while names and not names[-1]:
        names.pop()
    if not names:
        raise ValueError(f"Classes file is empty: {path}")
    if any(not name for name in names):
        raise ValueError(f"Classes file contains an empty line in the middle: {path}")
    return dict(enumerate(names))


def require_dir(path: Path, what: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"{what} folder not found: {path}")


def list_images(image_dir: Path) -> list:
    return sorted(
        (p for p in image_dir.iterdir()
         if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: p.name.lower(),
    )


def list_labels(label_dir: Path) -> list:
    return sorted(
        (p for p in label_dir.glob("*.txt") if p.is_file()),
        key=lambda p: p.name.lower(),
    )


def parse_label_line(line: str):
    """Parse 'class x_center y_center width height'.

    Returns (class_id, (x_center, y_center, width, height)).
    Raises ValueError with a readable message if the line is malformed.
    """
    parts = line.split()
    if len(parts) != 5:
        raise ValueError(f"expected 5 values, got {len(parts)}")
    try:
        class_id = int(parts[0])
    except ValueError:
        raise ValueError(f"class ID {parts[0]!r} is not an integer") from None
    try:
        box = tuple(float(p) for p in parts[1:])
    except ValueError:
        raise ValueError("invalid numeric value") from None
    if not all(math.isfinite(v) for v in box):
        raise ValueError("non-finite numeric value")
    return class_id, box


def format_label_line(class_id: int, box) -> str:
    """Format a label line with fixed precision (never scientific notation)."""
    return f"{class_id} " + " ".join(f"{v:.6f}" for v in box)


def to_corners(box):
    """(x_center, y_center, w, h) -> (x1, y1, x2, y2)."""
    x, y, w, h = box
    return x - w / 2, y - h / 2, x + w / 2, y + h / 2


def calculate_iou(box1, box2) -> float:
    ax1, ay1, ax2, ay2 = to_corners(box1)
    bx1, by1, bx2, by2 = to_corners(box2)

    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h

    union = box1[2] * box1[3] + box2[2] * box2[3] - inter
    if union <= 0:
        return 0.0
    return inter / union


def find_duplicates(entries, threshold: float = DUPLICATE_IOU_THRESHOLD):
    """Find duplicate boxes of the same class.

    entries: list of (line_number, class_id, box).
    Returns a list of (kept_line, duplicate_line, class_id, iou).
    The first box is kept; every later box that overlaps a kept box
    of the same class with IoU > threshold is a duplicate.
    """
    kept = []
    duplicates = []
    for line_number, class_id, box in entries:
        for kept_line, kept_class, kept_box in kept:
            if kept_class != class_id:
                continue
            iou = calculate_iou(kept_box, box)
            if iou > threshold:
                duplicates.append((kept_line, line_number, class_id, iou))
                break
        else:
            kept.append((line_number, class_id, box))
    return duplicates


def write_text_atomic(path: Path, text: str) -> None:
    """Write a file so that a crash never leaves it half-written."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
