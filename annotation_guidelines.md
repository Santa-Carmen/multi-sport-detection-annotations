# Annotation Guidelines: Ball and Player Detection in Team Sports

**Version:** 1.1
**Sports:** football (soccer), volleyball, basketball, water polo
**Task:** object detection (bounding boxes)

---

## 1. Goal

The dataset is used to train an object detection model that finds **players** and **balls** in photos from sports games. Consistent labeling matters more than perfect labeling: the same situation must always be labeled the same way, by every annotator.

## 2. Classes

| ID | Class | What it is |
|----|-------|-----------|
| 0 | `player` | A person actively taking part in the game on the field/court/pool: field players, goalkeepers, liberos |
| 1 | `ball` | The match ball of the given sport (football, volleyball, basketball, water polo ball) |

### What is NOT labeled

- Spectators, fans, photographers
- Coaches, referees, ball kids, medical staff, staff on the sidelines
- Players on the bench or warming up outside the playing area
- Reserve/spare balls lying outside the field, balls in the stands, balls on the ground next to the sideline that are not in play
- Balls in advertising, logos, banners, TV graphics
- Mannequins, statues, posters, screens showing the game

> Rule of thumb: if the person is not on the playing surface and not participating in the current play, do not label them.

Unlabeled people are **intentional**: the model must learn that "a person" is not automatically a `player`. Because of this, the class definition above must be applied strictly and identically across all images.

## 3. How to draw a bounding box

1. The box is **axis-aligned** (a rectangle with horizontal and vertical sides).
2. It must be **tight**: the edges touch the outermost visible pixels of the object. No large gaps, no cutting into the object.
3. Include everything that belongs to the object:
   - **player:** head, torso, arms, legs, shoes. Include worn equipment (gloves, cap, goggles). Do not include the shadow or the reflection in water.
   - **ball:** the full circle of the ball, including the part blurred by motion if the ball edge is still visible.
4. Do **not** include a held ball in a player's box just because the player holds it; the ball gets its own separate box. The player's box covers only the player's body and worn equipment, even if the held ball extends beyond it.
5. Boxes of different objects may overlap. Do not shrink a box to avoid overlap.
6. One object = one box. Never draw one box around a group of players.
7. Start the box from the top-left visible extremity and finish at the bottom-right, then check that no part of the object is outside the box.

**Water polo:** the player is often visible only from the chest up (the lower body is underwater). Label only the visible part above the water. Do not guess where the legs are.

## 4. Partially visible objects (occlusion)

- If **at least ~30%** of the object is visible, label it. Draw the box around the **visible part only** (do not extrapolate hidden parts).
- If **less than ~30%** is visible, or you cannot tell what it is, do not label it (if it is likely an object, use `ignore`, see section 8).
- A player occluded by another player: label both, each with the box around their own visible part.
- A ball hidden behind a hand or a foot: label the ball if at least ~30% of it is visible. A ball fully covered by a hand is not labeled.
- A ball partly hidden by the net, goal post, or basket: label the visible part if it is clearly a ball.

## 5. Blurred ball (motion blur, out of focus)

The ball is often the hardest object: small, fast, blurred.

- **Ball is blurred but you can clearly tell it is a ball** (round or oval shape, correct color/context): label it. Draw the box around the whole blurred shape, including the smear, as long as the smear looks like part of the ball's own shape.
- **Ball is stretched by motion blur:** box around the full visible streak, not only the sharpest point.
- **You are unsure it is a ball** (could be a shadow, a spot on the grass, a logo, a head in the background): do **not** guess. Mark it as `ignore` (section 8) or leave it unlabeled if it is very unlikely.
- **Do not use the game context to invent a ball.** If the ball is not visible, it is not labeled, even if the players are clearly looking at where it should be.
- Use the same decision for all sports: "Can an independent annotator, looking only at this crop, say it is a ball with reasonable confidence?" If yes, label it. If no, ignore.

## 6. Objects at the image edge

- If an object is **cut off by the image border**, label the **visible part**. The box goes up to the image edge (coordinates are clipped to the image boundaries).
- Do not make the box extend beyond the image.
- Apply the visibility threshold from section 4: if only a tiny piece (a hand, a foot, a small part of the ball) is visible at the edge, do not label it, or use `ignore` if it is ambiguous.
- Players at the edge who are clearly part of the game: label them normally, even if only half of the body is visible.

## 7. Small, distant and crowded objects

- **Small objects:** label them if they are at least ~8×8 pixels and clearly recognizable. Smaller than this: `ignore` or unlabeled.
- **Distant players** in wide shots: label them if you can tell they are on the field. If a whole group is too small to separate into individuals, do not draw a group box; use an `ignore` region.
- **Crowded scenes** (goal mouth in football, scrum near the net in volleyball, water polo battles): label each separately visible player. If a player is only a few pixels visible behind others, apply the visibility rule in section 4.
- **Multiple balls** in the frame (e.g. warm-up): label only the ball in play. Balls outside the playing area are not labeled.

## 8. When to use `ignore`

`ignore` marks a region or object that **must not count** in training as either a positive or a negative example. Use it when the correct answer is uncertain, not when you want to skip work.

Use `ignore` for:

1. A blurred or tiny object that **might be a ball**, but you cannot say for sure.
2. A **group of players too small or too dense** to separate into individual boxes.
3. A heavily **occluded or cropped** person or ball where the visible part is too small to label, but it clearly is an object of the class.
4. **Reflections, mirrors, screens** that show players or a ball.
5. **Ambiguous "is it a player?" cases**, e.g. a person at the boundary of the field who may be a substitute or a referee.
6. Objects in very poor image regions (heavy overexposure, dark shadows, strong compression artifacts).

Do **not** use `ignore` for:
- Objects that are clearly not part of the classes (spectators, referees). These are simply not labeled.
- Clear, easy objects you were too lazy to draw.

Draw an `ignore` box (or polygon around a crowd area) with a tight fit around the uncertain region. In the annotation tool, use a separate label `ignore`.

## 9. Sport-specific notes

| Sport | Players | Ball | Special cases |
|-------|---------|------|--------------|
| Football | Field players + goalkeepers on the pitch | Football, usually small and far away | Goalkeeper diving: box around the whole body; wide shots have tiny balls |
| Volleyball | Players on court; libero included | Volleyball, often blurred during spikes | Net can partially cover players and ball; players at the net are often overlapping |
| Basketball | Players on court | Basketball, often held or partly hidden by hands | Ball is often in a hand: box separately; ball in the basket: label if visible |
| Water polo | Players in the pool (visible part above water) | Water polo ball, often yellow, partially in water | Splashes hide the ball; reflection and water glare are not objects |

## 10. Quality control

- **Self-check:** before submitting, look at each image once more and check: no missing players on the court, boxes are tight, ball is labeled only when clearly visible.
- **Consistency check:** review 5–10% of the images a second time after a break; fix systematic differences (e.g. boxes that are too loose).
- **Second annotator (optional):** for a sample of images, compare two independent annotations. Compute IoU between matching boxes; a target of **IoU ≥ 0.7** for players and **≥ 0.5** for balls is reasonable (balls are small, so a few pixels change IoU a lot).
- **Disagreements:** if two annotators disagree on a case, discuss it and **add the decision as a new rule** to this document.
- **Automated checks:** run `python fix_box.py`, `python dedupe.py` and `python validate.py` after annotating (see the README). Fix every error reported by `validate.py`.
- **Version control:** every rule change increases the document version and is noted in the changelog below.

## 11. Common mistakes to avoid

- Labeling spectators, referees, or coaches as `player`.
- Loose boxes with large background margins, or boxes that cut off feet or hands.
- Labeling a ball that is not actually visible (guessing from context).
- Drawing one box around several players.
- Extending the box to hidden body parts.
- Forgetting the ball because it is small.
- Inconsistent treatment of the same situation across images.
- Using `ignore` for every hard case instead of making a decision.

## 12. Output format

- Format: YOLO (`class x_center y_center width height`, normalized to `[0, 1]`). This is the only supported format.
- Classes (see `classes.txt`): `0 player`, `1 ball`, `2 ignore`. `ignore` regions are stored in the same label file as class 2. Whoever uses the dataset (e.g. for training) is responsible for handling class 2 (masking or removing it).
- One annotation file per image, same base file name as the image.
- Empty file allowed: image with no labeled objects.

## Changelog

| Version | Change |
|---------|--------|
| 1.0 | First version of the guidelines |
| 1.1 | Unified the visibility threshold to ~30% (section 4); clarified that a held ball is never part of the player's box; YOLO is the only supported format and `ignore` is class 2 in the label files (section 12); added automated checks to section 10 |

## QC History

| Date | Action | Result |
|------|--------|--------|
| 2026-09-22 | Corrected annotation errors found during automated validation | Fixed bounding boxes that extended beyond the image boundaries |
| 2026-09-23 | Corrected annotation warnings found during automated validation | Removed duplicated bounding boxes that were placed at the same location in some annotation files |