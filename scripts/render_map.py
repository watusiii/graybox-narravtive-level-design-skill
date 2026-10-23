"""
render_map.py — draw a to-scale 2D blueprint map from the level file (.yaml or .json).

The level file is the source of truth (rooms, features, props, beats, all in meters on the 1m Metric).
Works for any game (e.g. Phase, OSL Shooter).

    python render_map.py                # auto-picks the level file in this folder
    python render_map.py lvl2.yaml      # or name one

Reads from input/, writes a to-scale, labeled SVG to output/.
Runs validate.py first; errors stop generation unless --force is passed.
"""

import os
import sys
from level_io import load_level_data, find_level_file, output_dir
from validate import validate_level

HERE = os.path.dirname(os.path.abspath(__file__))
S = 28          # pixels per meter
OX, OY = 70, 90  # map origin in px
BG, PANEL, GRID = "#141410", "#1b1b15", "#34342a"
STRUCT, INK, DIM, DANGER = "#e8b23a", "#e7dfc9", "#9a9788", "#ff3b30"


def X(m): return round(OX + m * S, 1)
def Y(m): return round(OY + m * S, 1)
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data):
    e = []  # svg elements
    rooms = data.get("rooms", [])
    if not rooms:
        right, bottom = OX + 600, OY + 400
    else:
        right = max(X(r["x"] + r["w"]) for r in rooms)
        bottom = max(Y(r["y"] + r["h"]) for r in rooms)
    vw, vh = right + 200, bottom + 100

    project_title = data.get("project", "TACTICAL BLUEPRINT").upper()
    level_title = data.get("level", "SCHEMATIC").upper()

    # header
    e.append(f'<text x="30" y="42" fill="{STRUCT}" font-size="22" font-weight="700" '
             f'letter-spacing="1">{esc(project_title)}</text>')
    e.append(f'<text x="31" y="64" fill="{DIM}" font-size="12.5" letter-spacing="1.5">'
             f'{esc(level_title)} · TOP-DOWN · 1 CELL = 1 M</text>')

    # grid
    e.append(f'<rect x="{OX}" y="{OY}" width="{right-OX}" height="{bottom-OY}" '
             f'fill="url(#grid)" opacity="0.5"/>')

    # rooms
    for r in rooms:
        e.append(f'<rect x="{X(r["x"])}" y="{Y(r["y"])}" width="{r["w"]*S}" height="{r["h"]*S}" '
                 f'fill="rgba(232,178,58,0.045)" stroke="{STRUCT}" stroke-width="2"/>')
        e.append(f'<text x="{X(r["x"])+16}" y="{Y(r["y"])+24}" fill="{STRUCT}" font-size="15" '
                 f'font-weight="700">{esc(r["label"])}</text>')
        e.append(f'<text x="{X(r["x"])+16}" y="{Y(r["y"])+41}" fill="{DIM}" font-size="11">'
                 f'{r["w"]} × {r["h"]} m</text>')

    # features
    for f in data.get("features", []):
        col = DANGER if f.get("danger") else STRUCT
        t = f["type"]
        if t == "wreck":
            e.append(f'<rect x="{X(f["x"])}" y="{Y(f["y"])}" width="{f["w"]*S}" height="{f["h"]*S}" '
                     f'fill="none" stroke="{STRUCT}" stroke-width="1.5" stroke-dasharray="5 4" opacity="0.8"/>')
            if f.get("label"):
                e.append(f'<text x="{X(f["x"])+8}" y="{Y(f["y"])+18}" fill="{STRUCT}" font-size="11" '
                         f'opacity="0.85">{esc(f["label"])}</text>')
        elif t == "block":
            fill = "rgba(255,59,48,0.18)" if f.get("danger") else PANEL
            e.append(f'<rect x="{X(f["x"])}" y="{Y(f["y"])}" width="{f["w"]*S}" height="{f["h"]*S}" '
                     f'fill="{fill}" stroke="{col}" stroke-width="1.5"/>')
            if f.get("label"):
                fs = 11 if f["w"] >= 2 else 9
                e.append(f'<text x="{X(f["x"]+f["w"]/2)}" y="{Y(f["y"]+f["h"]/2)+4}" fill="{col}" '
                         f'font-size="{fs}" text-anchor="middle">{esc(f["label"])}</text>')
        elif t == "door":
            if "h" in f:  # vertical door
                e.append(f'<line x1="{X(f["x"])}" y1="{Y(f["y"])}" x2="{X(f["x"])}" y2="{Y(f["y"]+f["h"])}" '
                         f'stroke="{col}" stroke-width="6" stroke-linecap="square"/>')
                if f.get("label"):
                    e.append(f'<text x="{X(f["x"])+10}" y="{Y(f["y"]+f["h"]/2)+4}" fill="{col}" '
                             f'font-size="11" font-weight="700">{esc(f["label"])}</text>')
            elif "w" in f:  # horizontal door
                e.append(f'<line x1="{X(f["x"])}" y1="{Y(f["y"])}" x2="{X(f["x"]+f["w"])}" y2="{Y(f["y"])}" '
                         f'stroke="{col}" stroke-width="6" stroke-linecap="square"/>')
                if f.get("label"):
                    e.append(f'<text x="{X(f["x"]+f["w"]/2)}" y="{Y(f["y"])-6}" fill="{col}" '
                             f'font-size="11" font-weight="700">{esc(f["label"])}</text>')
        elif t == "opening":
            if "h" in f:  # vertical opening
                e.append(f'<line x1="{X(f["x"])}" y1="{Y(f["y"])}" x2="{X(f["x"])}" y2="{Y(f["y"]+f["h"])}" '
                         f'stroke="{col}" stroke-width="2" stroke-dasharray="4 3" opacity="0.6"/>')
            elif "w" in f:  # horizontal opening
                e.append(f'<line x1="{X(f["x"])}" y1="{Y(f["y"])}" x2="{X(f["x"]+f["w"])}" y2="{Y(f["y"])}" '
                         f'stroke="{col}" stroke-width="2" stroke-dasharray="4 3" opacity="0.6"/>')
        elif t in ("vent", "grate"):
            e.append(f'<rect x="{X(f["x"])}" y="{Y(f["y"])}" width="{f["w"]*S}" height="{f["h"]*S}" '
                     f'fill="none" stroke="{col}" stroke-width="1.5" stroke-dasharray="3 3"/>')
            if f.get("label"):
                e.append(f'<text x="{X(f["x"]+f["w"]/2)}" y="{Y(f["y"]+f["h"]/2)+4}" fill="{col}" '
                         f'font-size="10" text-anchor="middle">{esc(f["label"])}</text>')

    # props
    for p in data.get("props", []):
        col = DANGER if p.get("danger") else STRUCT
        e.append(f'<circle cx="{X(p["x"])}" cy="{Y(p["y"])}" r="4.5" fill="{col}"/>')
        if p.get("label"):
            e.append(f'<text x="{X(p["x"])+8}" y="{Y(p["y"])+4}" fill="{col}" font-size="10.5" '
                     f'font-weight="600">{esc(p["label"])}</text>')

    # path
    def draw_path(pts, stroke, dash=""):
        if not pts or len(pts) < 2: return
        d = "M " + " L ".join(f"{X(p[0])} {Y(p[1])}" for p in pts)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        e.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="2"{dash_attr} opacity="0.85"/>')

    draw_path(data.get("path", []), STRUCT, "6 4")
    draw_path(data.get("path_return", []), DANGER, "4 4")

    # beats
    for b in data.get("beats", []):
        col = DANGER if b.get("danger") else STRUCT
        e.append(f'<circle cx="{X(b["x"])}" cy="{Y(b["y"])}" r="10" fill="{BG}" stroke="{col}" stroke-width="2"/>')
        e.append(f'<text x="{X(b["x"])}" y="{Y(b["y"])+4}" fill="{col}" font-size="11" '
                 f'font-weight="700" text-anchor="middle">{b["n"]}</text>')

    # legend
    ly = bottom + 30
    e.append(f'<text x="{OX}" y="{ly}" fill="{STRUCT}" font-size="13" font-weight="700" '
             f'letter-spacing="1">BEATS &amp; OBJECTIVES</text>')
    ly += 20
    for b in data.get("beats", []):
        col = DANGER if b.get("danger") else STRUCT
        txt = f'{b["n"]}. {esc(b["label"])}'
        if b.get("objective"):
            txt += f' — [OBJ: {esc(b["objective"])}]'
        e.append(f'<text x="{OX}" y="{ly}" fill="{col}" font-size="11.5">{txt}</text>')
        ly += 18

    body = "\n".join(e)
    return (
        f'<svg viewBox="0 0 {round(vw)} {round(vh)}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" font-family="Cascadia Mono, Consolas, ui-monospace, monospace">\n'
        f'<title>{esc(level_title)} — top-down schematic to scale.</title>\n'
        f'<defs><pattern id="grid" width="{2*S}" height="{2*S}" patternUnits="userSpaceOnUse">'
        f'<path d="M{2*S} 0H0V{2*S}" fill="none" stroke="{GRID}" stroke-width="1"/></pattern></defs>\n'
        f'<rect x="0" y="0" width="{round(vw)}" height="{round(vh)}" fill="{BG}"/>\n'
        f'{body}\n</svg>\n'
    )


if __name__ == "__main__":
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

    svg = render(data)

    stem = os.path.splitext(os.path.basename(level_path))[0]
    out_name = "vslice-map.svg" if stem == "vslice" else f"{stem}-map.svg"
    out = os.path.join(output_dir(HERE), out_name)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {out}  ({len(svg)} bytes) from {os.path.basename(level_path)}")
