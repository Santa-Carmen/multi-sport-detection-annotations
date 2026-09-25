# Ball and Player Detection in Team Sports: Annotation Project

A data annotation project: bounding-box labels for **players** and **balls** in photos from team sports games, together with the annotation guidelines and small utility scripts that keep the annotations clean and consistent.

**Sports covered:** football (soccer), volleyball, basketball, water polo
**Annotation format:** YOLO (`class x_center y_center width height`, normalized to `[0, 1]`)

This repository contains annotations only. It does not include any model training code or a train/val/test split.

---

## Project structure

```
.
├── images/                   # source photos (.jpg, .jpeg, .png, .bmp, .webp)
├── labels/                   # one YOLO .txt file per image (same base name)
├── classes.txt               # class names, one per line (line number = class ID)
├── annotation_guidelines.md  # rules every annotator must follow
├── common.py                 # helpers shared by the scripts
├── validate.py               # dataset validation (errors + warnings + statistics)
├── fix_box.py                # clips boxes that stick out of the image
├── dedupe.py                 # removes duplicate boxes
├── remove_unannotated.py     # moves images without a label file out of images/
├── visualize_annotations.py   # creates copies with colored annotation boxes
├── annotated_images/          # generated visual-review images (created on demand)
├── requirements.txt
└── .gitignore
```

## Classes

| ID | Class    | Description |
|----|----------|-------------|
| 0  | `player` | A person actively taking part in the game on the field/court/pool (field players, goalkeepers, liberos) |
| 1  | `ball`   | The match ball in play |
| 2  | `ignore` | A region or object that is too uncertain to count as either a positive or a negative example |

Spectators, coaches, referees, bench players, spare balls and balls on banners/screens are **intentionally not labeled**. See [`annotation_guidelines.md`](annotation_guidelines.md) for the full rules (occlusion, motion blur, image edges, small and crowded objects, sport-specific cases).

`ignore` regions are stored in the label files as class 2. Anyone who uses the dataset for training is responsible for masking or removing them.

## Label format

Each `labels/<image_name>.txt` contains one line per object:

```
<class_id> <x_center> <y_center> <width> <height>
```

- All four values are normalized to `[0, 1]` by the image width/height.
- The box must lie fully inside the image.
- An empty file means "image with no labeled objects". Every image must have a label file, even if it is empty.

Example:

```
0 0.512000 0.634000 0.081000 0.312000
1 0.487000 0.402000 0.017000 0.030000
```

## Requirements

- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/)

```bash
pip install -r requirements.txt
```

## Scripts

By default every script expects `images/`, `labels/` and `classes.txt` next to it. Other locations can be passed with `--images`, `--labels` and `--classes` (run a script with `--help` to see its options).

### `validate.py`: check the dataset

```bash
python validate.py            # exit code 1 if there are errors
python validate.py --strict   # exit code 1 if there are warnings too
```

Prints the number of images and boxes per class, then:

**Errors** (must be fixed):
- image cannot be opened
- missing label file
- line does not have 5 values, or contains invalid numbers
- unknown class ID (checked against `classes.txt`)
- coordinates outside `[0, 1]`, zero or negative box size
- box extends beyond the image
- two images with the same base name (they would share one label file)

**Warnings** (should be reviewed):
- duplicate boxes of the same class (IoU > 0.95)
- box smaller than 8 px on a side (guidelines, section 7; `ignore` regions are exempt)
- ball box larger than 25% of the image on a side (heuristic)
- label file without a matching image
- unsupported files in `images/`

Coordinates are compared with a tolerance of `1e-6` to avoid false errors caused by floating-point rounding.

### `fix_box.py`: clip boxes to the image

```bash
python fix_box.py --dry-run   # show what would change
python fix_box.py
```

- Boxes that stick out by a small amount (up to 2% of the image size, `--max-clip`) are clipped to the image boundary.
- Boxes completely outside the image are removed.
- Larger overshoots are **not** changed. They are listed for manual review, because they are usually annotation mistakes.
- All other lines are kept exactly as they are; files are written atomically.

### `dedupe.py`: remove duplicate boxes

```bash
python dedupe.py --dry-run
python dedupe.py
```

For boxes of the same class with IoU above 0.95 (`--threshold`) the first one is kept and the others are removed.

### `remove_unannotated.py`: move unannotated images away

```bash
python remove_unannotated.py           # dry run
python remove_unannotated.py --apply   # move the images
```

Images that have no label file are moved to `removed_images/` (not deleted, so the step can be undone). Labels without an image are only reported. The script refuses to run if no image has a label file (usually a wrong `--labels` path).

> An image with an **empty** label file is kept. Make sure your annotation tool exports an empty `.txt` file for images without objects, otherwise they will be treated as unannotated.

### `visualize_annotations.py`: create annotated preview images

```bash
python visualize_annotations.py
```

The script creates `annotated_images/` and saves a copy of every image that has a matching file in `labels/`. It draws each YOLO bounding box in a distinct color for its class and adds the class name. Images without a label file are skipped; the originals and label files are never changed.

To use different folders:

```bash
python visualize_annotations.py --images path/to/images --labels path/to/labels --output path/to/previews
```

## Recommended workflow

1. Annotate images following `annotation_guidelines.md`.
2. Export labels in YOLO format into `labels/`.
3. `python fix_box.py`: clip boxes that go slightly outside the image.
4. `python dedupe.py`: remove duplicate boxes.
5. `python validate.py`: fix everything that is reported.
6. `python visualize_annotations.py`: inspect the colored preview images in `annotated_images/`.
7. (Optional) `python remove_unannotated.py --apply`: move images that were never annotated.
8. Review 5–10% of the images a second time (section 10 of the guidelines).

## Quality control

Consistency matters more than perfection. The guidelines describe self-checks, a second-annotator comparison (target IoU ≥ 0.7 for players, ≥ 0.5 for balls) and how new rules are added when annotators disagree. The QC history is kept at the end of `annotation_guidelines.md`.

## Dataset statistics

Run `python validate.py` to get the current numbers.

| Item | Value |
|------|-------|
| Images | 22 |
| `player` boxes | 85 |
| `ball` boxes | 22 |
| `ignore` regions | 13 |

## Data source and license

_TBD: describe where the images come from and under which license they can be used and redistributed._

## Storage tip

If the repository is hosted on GitHub, consider [Git LFS](https://git-lfs.com/) or external storage for `images/`.

## Versioning

The guidelines are versioned (see the changelog in `annotation_guidelines.md`). Every rule change increases the version number.
