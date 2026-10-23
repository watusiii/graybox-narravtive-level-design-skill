"""
level_io.py — shared loader + wall builder for the graybox generators.

Level files are YAML (.yaml / .yml) or JSON (.json). YAML is preferred:
lighter for an LLM to write, easy to hand-edit, and allows # comments.

All three generators (render_map, gen_walkthrough, gen_blender) import this,
so loading and wall logic live in exactly one place.
"""
import json
import os
import sys

WALL_H, WALL_T = 4.0, 0.24
DOOR_TOP = 3.4      # door openings leave a lintel above this height
GRATE_TOP = 2.0     # crawl grates punch a 2 m hole in the wall
EPS = 0.01

LEVEL_EXTS = (".yaml", ".yml", ".json")
PREFERRED = ["level.yaml", "level.yml", "vslice.yaml", "level.json", "vslice.json"]


# ---------------------------------------------------------------- loading

def load_level_data(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            sys.exit("PyYAML is needed to read .yaml levels. Run:  python -m pip install pyyaml  (or py on Windows)")
        data = yaml.safe_load(text)
    elif ext == ".json":
        data = json.loads(text)
    elif ext == ".toon":
        sys.exit(f"{os.path.basename(path)}: .toon is no longer supported. "
                 f"If it's indented 'key: value' style it is already YAML; rename it to .yaml.")
    else:
        sys.exit(f"Unknown level file type: {path}")
    if not isinstance(data, dict):
        sys.exit(f"{os.path.basename(path)}: top level must be a mapping (project:, level:, rooms: ...)")
    # an empty YAML key ("props:") loads as None — treat it as an empty list
    for k in ("rooms", "features", "props", "beats", "path", "path_return", "notes"):
        if data.get(k) is None and k in data:
            data[k] = []
    return data


def input_dir(here):
    """Level files live in <scripts>/input/ (falls back to the scripts folder itself)."""
    d = os.path.join(here, "input")
    return d if os.path.isdir(d) else here


def output_dir(here):
    """Everything generated goes to <scripts>/output/."""
    d = os.path.join(here, "output")
    os.makedirs(d, exist_ok=True)
    return d


def find_level_file(here):
    """argv[1] if given (a path, or just a name inside input/), else the level file in input/."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        for p in (os.path.abspath(arg), os.path.join(input_dir(here), arg)):
            if os.path.exists(p):
                return p
        sys.exit(f"Level file not found: {arg}  (looked here and in {input_dir(here)})")
    here = input_dir(here)
    for name in PREFERRED:
        p = os.path.join(here, name)
        if os.path.exists(p):
            return p

    found, problems = [], []
    for f in sorted(os.listdir(here)):
        ext = os.path.splitext(f)[1].lower()
        if f.endswith(".toon"):
            problems.append(f"{f}: .toon files are skipped — rename to .yaml")
            continue
        if ext not in LEVEL_EXTS or f.startswith("package"):
            continue
        p = os.path.join(here, f)
        try:
            d = load_level_data(p)
        except SystemExit as e:
            problems.append(str(e)); continue
        except Exception as e:  # parse error: say so, don't hide it
            problems.append(f"{f}: could not parse — {e}"); continue
        if "rooms" in d or "beats" in d:
            found.append(p)

    for msg in problems:
        print("WARNING:", msg)
    if not found:
        sys.exit(f"No level file (.yaml / .json) found in {here}")
    # prefer YAML over JSON when both exist
    found.sort(key=lambda p: (not p.lower().endswith((".yaml", ".yml")), p))
    if len(found) > 1:
        names = ", ".join(os.path.basename(p) for p in found)
        print(f"NOTE: several level files here ({names}); using {os.path.basename(found[0])}. "
              f"Pass a filename to pick another, e.g.  py render_map.py lvl1.json")
    return found[0]


# ---------------------------------------------------------------- walls

def _union(intervals):
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1] + EPS:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _subtract(spans, a, b):
    out = []
    for s, e in spans:
        if b <= s + EPS or a >= e - EPS:
            out.append((s, e)); continue
        if a > s + EPS: out.append((s, a))
        if b < e - EPS: out.append((b, e))
    return out


def build_walls(data):
    """
    Walls come from room outlines. Shared edges between rooms merge into one wall.
    Holes are cut by:
      door     (x = wall line, y..y+h)  -> opening with lintel; the door slab is drawn separately
      opening  (x = wall line, y..y+h)  -> open gap, nothing drawn (e.g. an alcove open to a hall)
      grate    (any rect crossing a horizontal wall) -> 2 m crawl hole
    Returns boxes: {name, x, z, w, d, h, y0}   (x/z = min corner on the floor plane, meters)
    """
    lines = {}  # ("X", z) horizontal wall at z, spans along x | ("Z", x) vertical wall at x, spans along z
    for r in data.get("rooms", []):
        x, z, w, h = r["x"], r["y"], r["w"], r["h"]
        lines.setdefault(("X", z), []).extend([(x, x + w)])
        lines.setdefault(("X", z + h), []).extend([(x, x + w)])
        lines.setdefault(("Z", x), []).extend([(z, z + h)])
        lines.setdefault(("Z", x + w), []).extend([(z, z + h)])

    holes = {k: [] for k in lines}  # key -> [(a, b, top)]
    for f in data.get("features", []):
        t = f.get("type")
        if t in ("door", "opening"):
            top = DOOR_TOP if t == "door" else WALL_H
            # Vertical door/opening: has h, sits on vertical wall at x
            if "h" in f:
                for (axis, c) in lines:
                    if axis == "Z" and abs(c - f["x"]) < 0.5:
                        holes[(axis, c)].append((f["y"], f["y"] + f["h"], top))
            # Horizontal door/opening: has w, sits on horizontal wall at y
            elif "w" in f:
                for (axis, c) in lines:
                    if axis == "X" and abs(c - f["y"]) < 0.5:
                        holes[(axis, c)].append((f["x"], f["x"] + f["w"], top))
        elif t == "grate":
            for (axis, c) in lines:
                if axis == "X" and f["y"] - EPS <= c <= f["y"] + f["h"] + EPS:
                    holes[(axis, c)].append((f["x"], f["x"] + f["w"], GRATE_TOP))

    boxes = []
    for (axis, c), spans in sorted(lines.items()):
        spans = [tuple(s) for s in _union(spans)]
        tag = f"wall_{'H' if axis == 'X' else 'V'}{c:g}"
        for a, b, top in holes[(axis, c)]:
            spans = _subtract(spans, a, b)
            if top < WALL_H - EPS:
                boxes.append(_wall_box(axis, c, a, b, WALL_H - top, top, tag + "_lintel"))
        for a, b in spans:
            if b - a > EPS:
                boxes.append(_wall_box(axis, c, a, b, WALL_H, 0.0, tag))
    return boxes


def _wall_box(axis, c, a, b, h, y0, name):
    if axis == "X":
        return {"name": name, "x": a, "z": c - WALL_T / 2, "w": b - a, "d": WALL_T, "h": h, "y0": y0}
    return {"name": name, "x": c - WALL_T / 2, "z": a, "w": WALL_T, "d": b - a, "h": h, "y0": y0}


def floor_bounds(data, pad=1.0):
    rooms = data.get("rooms", [])
    if not rooms:
        return (-1, -1, 30, 30)
    x1 = min(r["x"] for r in rooms) - pad
    z1 = min(r["y"] for r in rooms) - pad
    x2 = max(r["x"] + r["w"] for r in rooms) + pad
    z2 = max(r["y"] + r["h"] for r in rooms) + pad
    return (x1, z1, x2 - x1, z2 - z1)
