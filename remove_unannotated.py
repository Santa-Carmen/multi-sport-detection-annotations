"""Move images that have no label file out of the images folder.

Usage:
    python remove_unannotated.py            # dry run: only shows what would happen
    python remove_unannotated.py --apply    # really moves the images

Images are MOVED to a separate folder (default: ./removed_images), not deleted,
so the operation can be undone. Labels without an image are only reported.

Note: an image with an EMPTY label file is kept (it means "no objects").
Make sure your annotation tool exports an empty .txt file for such images,
otherwise they will be treated as unannotated.
"""

import argparse
import shutil
import sys
from pathlib import Path

from common import (
    PROJECT_DIR,
    add_path_args,
    list_images,
    list_labels,
    require_dir,
)


def unique_destination(folder: Path, name: str) -> Path:
    dest = folder / name
    counter = 1
    while dest.exists():
        dest = folder / f"{Path(name).stem}_{counter}{Path(name).suffix}"
        counter += 1
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_path_args(parser)
    parser.add_argument("--apply", action="store_true",
                        help="actually move the images (default is a dry run)")
    parser.add_argument("--removed-dir", type=Path,
                        default=PROJECT_DIR / "removed_images",
                        help="where to move images (default: ./removed_images)")
    args = parser.parse_args()

    try:
        require_dir(args.images, "Image")
        require_dir(args.labels, "Label")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 2

    images = list_images(args.images)
    labels = list_labels(args.labels)
    label_stems = {p.stem for p in labels}
    image_stems = {p.stem for p in images}

    to_remove = [p for p in images if p.stem not in label_stems]
    kept = [p for p in images if p.stem in label_stems]
    orphan_labels = [p for p in labels if p.stem not in image_stems]

    # Safety net: a wrong --labels path would otherwise remove everything.
    if images and not kept:
        print("ERROR: none of the images has a label file. "
              "Wrong labels folder? Nothing was moved.")
        return 2

    print("=" * 50)
    print("CLEANUP RESULT" + ("" if args.apply else " (dry run)"))
    print("=" * 50)
    print(f"Images found:       {len(images)}")
    print(f"Label files found:  {len(labels)}")
    print(f"Images kept:        {len(kept)}")
    print(f"Images to remove:   {len(to_remove)}")

    if to_remove:
        print("\nImages without a label file:")
        for path in to_remove:
            print(f"  - {path.name}")

        if args.apply:
            args.removed_dir.mkdir(parents=True, exist_ok=True)
            for path in to_remove:
                shutil.move(str(path), str(unique_destination(args.removed_dir, path.name)))
            print(f"\nMoved {len(to_remove)} image(s) to {args.removed_dir}")
        else:
            print("\nDry run: nothing was moved. Use --apply to move these images.")

    if orphan_labels:
        print("\nLabels without a matching image (not touched):")
        for path in orphan_labels:
            print(f"  - {path.name}")

    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
