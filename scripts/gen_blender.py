"""
gen_blender.py — bake a level file (.yaml or .json) into a Blender/Unity-ready OBJ.

    python gen_blender.py               # auto-picks the level file in this folder
    python gen_blender.py lvl2.yaml     # or name one

Import in Blender: File > Import > Wavefront (.obj). Units are meters, 1:1.
Every footprint arrives as a separate named object (KIOSK, BIO_CRATES, wall_H6...)
so the graybox works as a replace-in-place template: model the real asset, swap it,
position is already correct. Walls come from the same builder the walkthrough uses.
Runs validate.py first; errors stop generation unless --force is passed.
"""
import os
import re
import sys
from level_io import load_level_data, find_level_file, build_walls, floor_bounds, output_dir, WALL_H
from validate import validate_level

HERE = os.path.dirname(os.path.abspath(__file__))


def height_for(f):
    """Return explicit height or default 1.2m."""
    return f.get("height", 1.2)


def y0_for(f):
    """Return explicit y0 (height off floor) or ground level."""
    return f.get("y0", 0.0)


class Obj:
    def __init__(self):
        self.lines, self.vi = [], 1
        self.counts = {}

    def name(self, base):
        base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_") or "obj"
        n = self.counts.get(base, 0) + 1
        self.counts[base] = n
        return base if n == 1 else f"{base}_{n}"

    def box(self, name, x, z, w, d, h, y0=0.0):
        # OBJ is y-up; ground plane is xz. Blender's importer converts axes.
        self.lines.append(f"o {self.name(name)}")
        v = self.vi
        for yy in (y0, y0 + h):
            for xx, zz in ((x, z), (x + w, z), (x + w, z + d), (x, z + d)):
                self.lines.append(f"v {xx:.4f} {yy:.4f} {zz:.4f}")
        f_ = lambda a, b, c, dd: self.lines.append(f"f {v+dd} {v+c} {v+b} {v+a}")  # CCW = outward
        f_(0, 3, 2, 1); f_(4, 5, 6, 7)          # bottom, top
        f_(0, 1, 5, 4); f_(1, 2, 6, 5)          # sides
        f_(2, 3, 7, 6); f_(3, 0, 4, 7)
        self.vi += 8


def main():
    level_path = find_level_file(HERE)
    data = load_level_data(level_path)
    level_name = os.path.basename(level_path)

    # Run validator first
    force = "--force" in sys.argv
    errors, warnings = validate_level(data, level_name)
    if errors:
        print(f"ERRORS in {level_name}:")
        for e in errors:
            print(f"  ERROR: {e}")
        if not force:
            print(f"\nGeneration stopped. Fix errors above or use --force to generate anyway.")
            sys.exit(1)
        print(f"\n--force passed; generating despite errors.\n")
    if warnings:
        print(f"WARNINGS in {level_name}:")
        for w in warnings:
            print(f"  WARNING: {w}")
        print()

    project_title = data.get("project", "TACTICAL GRAYBOX")
    level_title = data.get("level", "LEVEL")
    stem = os.path.splitext(os.path.basename(level_path))[0]

    o = Obj()
    fx, fz, fw, fd = floor_bounds(data)
    o.box("FLOOR", fx, fz, fw, fd, 0.05, -0.05)

    for w in build_walls(data):
        o.box(w["name"], w["x"], w["z"], w["w"], w["d"], w["h"], w["y0"])

    for f in data.get("features") or []:
        t, l = f.get("type"), f.get("label") or ""
        if t == "block":
            o.box(l or "fixture", f["x"], f["y"], f["w"], f["h"], height_for(f), y0_for(f))
        elif t == "wreck":
            if "GANTRY" in l.upper():
                o.box("GANTRY_RAIL", f["x"], f["y"], f["w"], f["h"], 0.25, 3.1)
            else:
                o.box(l or "wreck", f["x"], f["y"], f["w"], f["h"], 2.8)
        elif t == "door":
            if "h" in f:  # vertical door
                x = -0.17 if f["x"] < 1 else f["x"] - 0.17
                o.box(l or "door", x, f["y"], 0.34, f["h"], 3.4)
            elif "w" in f:  # horizontal door
                y = -0.17 if f["y"] < 1 else f["y"] - 0.17
                o.box(l or "door", f["x"], y, f["w"], 0.34, 3.4)
        elif t == "vent":
            o.box(l or "vent", f["x"], f["y"], f["w"], 0.3, 0.9, 2.6)

    for p in data.get("props") or []:
        o.box("prop_" + (p.get("label") or "marker"), p["x"] - 0.15, p["y"] - 0.15, 0.3, 0.3, 1.0)

    out = os.path.join(output_dir(HERE), f"{stem}_graybox.obj")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# {project_title} // {level_title} graybox — generated from {os.path.basename(level_path)}\n")
        fh.write("\n".join(o.lines) + "\n")
    print(f"wrote {out}  ({len(o.lines)} lines, {len(o.counts)} object names) from {os.path.basename(level_path)}")


if __name__ == "__main__":
    main()
