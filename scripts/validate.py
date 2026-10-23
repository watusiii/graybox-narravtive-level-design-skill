"""
validate.py — catch level design errors before rendering.

Checks for broken paths, missing state flags, unreachable beats, and malformed data.
Run standalone or via the generators (render_map, gen_walkthrough, gen_blender).

    python validate.py                # auto-picks the level file in input/
    python validate.py lvl2.yaml      # or name one

Exit codes:
    0 = clean (may have warnings)
    1 = errors found (generation should stop unless --force is passed)
"""
import os
import sys
from level_io import load_level_data, find_level_file, build_walls, input_dir

HERE = os.path.dirname(os.path.abspath(__file__))
EPS = 0.01


def point_in_room(x, y, room):
    """Check if point (x, y) is inside a room."""
    return (room["x"] - EPS <= x <= room["x"] + room["w"] + EPS and
            room["y"] - EPS <= y <= room["y"] + room["h"] + EPS)


def segment_crosses_box(x1, y1, x2, y2, bx, by, bw, bh):
    """Check if line segment from (x1, y1) to (x2, y2) crosses box at (bx, by, bw, bh)."""
    # Simple AABB line intersection
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < EPS and abs(dy) < EPS:
        return False

    # Parametric line: p(t) = (x1, y1) + t * (dx, dy), t in [0, 1]
    t_min, t_max = 0.0, 1.0

    # Check x bounds
    if abs(dx) > EPS:
        t1 = (bx - x1) / dx
        t2 = (bx + bw - x1) / dx
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
    else:
        if not (bx <= x1 <= bx + bw):
            return False

    # Check y bounds
    if abs(dy) > EPS:
        t1 = (by - y1) / dy
        t2 = (by + bh - y1) / dy
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
    else:
        if not (by <= y1 <= by + bh):
            return False

    return t_min <= t_max


def validate_level(data, level_name="level"):
    """
    Validate level data, return (errors, warnings) as lists of strings.
    """
    errors, warnings = [], []

    rooms = data.get("rooms", [])
    features = data.get("features", [])
    props = data.get("props", [])
    beats = data.get("beats", [])
    path = data.get("path", [])

    # --- Check required fields ---
    for i, r in enumerate(rooms):
        if not all(k in r for k in ("id", "x", "y", "w", "h")):
            errors.append(f"Room {i}: missing required fields (id, x, y, w, h)")

    for i, b in enumerate(beats):
        if not all(k in b for k in ("n", "x", "y", "label")):
            errors.append(f"Beat {i}: missing required fields (n, x, y, label)")

    # Check for doors with neither h nor w
    for i, f in enumerate(features):
        if f.get("type") == "door":
            if "h" not in f and "w" not in f:
                errors.append(f"Door '{f.get('label', f'#{i}')}': must have either 'h' (vertical) or 'w' (horizontal)")

    # --- Check beat numbers ---
    beat_nums = [b["n"] for b in beats if "n" in b]
    if beat_nums:
        seen = set()
        for n in beat_nums:
            if n in seen:
                errors.append(f"Duplicate beat number: {n}")
            seen.add(n)

        # Check sequential (should be 1, 2, 3, ... N)
        expected = list(range(1, len(beat_nums) + 1))
        if sorted(beat_nums) != expected:
            errors.append(f"Beat numbers not sequential: expected {expected}, got {sorted(beat_nums)}")

    # --- Check state flags ---
    # Collect all flags set by beats, in order
    flags_set_by_beat = {}  # beat_n -> set of flags
    all_flags_set = set()
    for b in beats:
        if "n" not in b:
            continue
        flags = set((b.get("set_state") or {}).keys())
        flags_set_by_beat[b["n"]] = flags
        all_flags_set.update(flags)

    # Check that every requires_state flag is set by some earlier beat
    for b in beats:
        if "n" not in b:
            continue
        req = b.get("requires_state") or {}
        for flag in req.keys():
            # Check if this flag is set by any beat before this one
            set_before = any(flag in flags_set_by_beat.get(n, set())
                           for n in range(1, b["n"]))
            if not set_before:
                errors.append(f"Beat {b['n']} '{b.get('label', '')}': requires_state '{flag}' "
                            f"is never set by any earlier beat")

        # Warning: interact beat with requires_state but no denied_dialogue
        if b.get("trigger_type") == "interact" and req and not b.get("denied_dialogue"):
            warnings.append(f"Beat {b['n']} '{b.get('label', '')}': has requires_state "
                          f"but no denied_dialogue (player won't know why it's locked)")

    # Check that every door's opens_when flag is set by some beat
    for f in features:
        if f.get("type") == "door" and f.get("opens_when"):
            for flag in f["opens_when"].keys():
                if flag not in all_flags_set:
                    errors.append(f"Door '{f.get('label', 'unlabeled')}': opens_when '{flag}' "
                                f"is never set by any beat")

    # --- Check points inside rooms ---
    if rooms:
        for b in beats:
            if "x" not in b or "y" not in b:
                continue
            if not any(point_in_room(b["x"], b["y"], r) for r in rooms):
                errors.append(f"Beat {b.get('n', '?')} '{b.get('label', '')}' at ({b['x']}, {b['y']}) "
                            f"is outside every room")

        for p in props:
            if "x" not in p or "y" not in p:
                continue
            if not any(point_in_room(p["x"], p["y"], r) for r in rooms):
                errors.append(f"Prop '{p.get('label', 'unlabeled')}' at ({p['x']}, {p['y']}) "
                            f"is outside every room")

        for i, pt in enumerate(path):
            if len(pt) < 2:
                continue
            x, y = pt[0], pt[1]
            if not any(point_in_room(x, y, r) for r in rooms):
                errors.append(f"Path point {i} at ({x}, {y}) is outside every room")

    # --- Check path crosses walls ---
    # Build wall collider boxes from level_io
    try:
        wall_boxes = build_walls(data)
    except Exception as e:
        errors.append(f"Failed to build walls for path check: {e}")
        wall_boxes = []

    # Collect door/opening positions (vertical walls: x = wall, y..y+h; horizontal: y = wall, x..x+w)
    doors_and_openings = []
    for f in features:
        t = f.get("type")
        if t in ("door", "opening"):
            if "h" in f:  # vertical wall
                doors_and_openings.append(("V", f["x"], f["y"], f["y"] + f["h"]))
            elif "w" in f:  # horizontal wall
                doors_and_openings.append(("H", f["y"], f["x"], f["x"] + f["w"]))

    def is_door_here(wall_box):
        """Check if a door/opening covers this wall segment."""
        # wall_box has x, z, w, d, h, y0
        # Vertical wall: small d (depth), spans along z
        # Horizontal wall: small w (width), spans along x
        wx, wz, ww, wd = wall_box["x"], wall_box["z"], wall_box["w"], wall_box["d"]

        if wd < 0.5:  # vertical wall (along z-axis)
            wall_x = wx + ww / 2
            wall_y_start, wall_y_end = wz, wz + wd
            for axis, x, a, b in doors_and_openings:
                if axis == "V" and abs(x - wall_x) < 0.5:
                    # Check if door span overlaps wall span
                    if not (b < wall_y_start - EPS or a > wall_y_end + EPS):
                        return True
        elif ww < 0.5:  # horizontal wall (along x-axis)
            wall_y = wz + wd / 2
            wall_x_start, wall_x_end = wx, wx + ww
            for axis, y, a, b in doors_and_openings:
                if axis == "H" and abs(y - wall_y) < 0.5:
                    if not (b < wall_x_start - EPS or a > wall_x_end + EPS):
                        return True
        return False

    # Check each path segment
    for i in range(len(path) - 1):
        if len(path[i]) < 2 or len(path[i + 1]) < 2:
            continue
        x1, y1 = path[i][0], path[i][1]
        x2, y2 = path[i + 1][0], path[i + 1][1]

        for w in wall_boxes:
            # Skip elevated walls (lintels, wall-mounted objects) - paths are ground-level
            if w.get("y0", 0.0) > 0.5:
                continue

            # Wall is a box at (x, z) with dimensions (w, d, h)
            # Check if path segment crosses this wall box (ignoring height for now)
            if segment_crosses_box(x1, y1, x2, y2, w["x"], w["z"], w["w"], w["d"]):
                # Check if there's a door here
                if not is_door_here(w):
                    errors.append(f"Path crosses wall '{w['name']}' between "
                                f"({x1:.1f}, {y1:.1f}) and ({x2:.1f}, {y2:.1f}) "
                                f"with no door or opening")

    # --- Check for rooms with no beats ---
    if rooms and beats:
        for r in rooms:
            has_beat = any(point_in_room(b["x"], b["y"], r) for b in beats if "x" in b and "y" in b)
            if not has_beat:
                warnings.append(f"Room '{r.get('label', r.get('id', 'unlabeled'))}' has no beats in it "
                              f"(may be intentional for a hallway)")

    return errors, warnings


def main():
    level_path = find_level_file(HERE)
    data = load_level_data(level_path)
    level_name = os.path.basename(level_path)

    errors, warnings = validate_level(data, level_name)

    if errors:
        print(f"ERRORS in {level_name}:")
        for e in errors:
            print(f"  ERROR: {e}")
        print()

    if warnings:
        print(f"WARNINGS in {level_name}:")
        for w in warnings:
            print(f"  WARNING: {w}")
        print()

    if not errors and not warnings:
        print(f"PASS: {level_name} passes validation (no errors or warnings)")
        return 0
    elif not errors:
        print(f"PASS: {level_name} passes validation ({len(warnings)} warning(s))")
        return 0
    else:
        print(f"FAIL: {level_name} has {len(errors)} error(s), {len(warnings)} warning(s)")
        print(f"  Fix errors before generating. Use --force in generators to override.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
