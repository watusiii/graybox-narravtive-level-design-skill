---
name: graybox-level-design
description: Generate a NEW game level from scratch by conversation, data-first, with a YAML level file as the source of truth. Use when the user wants to create, generate, start, or block out a new level, room, area, or map ("make a new level", "generate the next level", "design the next area", "block out the research lab", "new graybox", "walkthrough for Phase"). Works for any narrative, top-down, tactical, or isometric game (e.g. Phase, OSL Shooter). Bootstraps a level folder with its own level.yaml and generators that render a 2D map, a 3D walkable browser graybox with tactile dialogue, and an engine-ready OBJ.
---

# Graybox Level Design — Data-First Narrative Level Generator

Levels are born as **data**: each level is a folder with one source of truth, `level.yaml`. Generators render the 2D SVG map, the interactive 3D browser walkthrough with in-world dialogue, and the 3D OBJ mesh. The conversation IS the design tool.

**Format: YAML.** Always write new levels as `level.yaml` (JSON still loads, for old levels). YAML is lighter than JSON to write, reads cleanly, and allows `# comments` for design notes. Do not use TOON.

**Edit, don't rewrite.** When the design changes, change only the beat, room, or feature that changed. Don't regenerate the whole file — that's where the real token cost is.

---

## Phase 0 — Context Discovery Before Geometry

Never assume hardcoded paths. Before designing or generating geometry:

1. **Check Current Working Directory First**:
   - Inspect the current directory and its parent/child subtrees for project documentation, design bibles, lore notes, character manifests, or existing level folders:
     - Folders like `docs/`, `Documentation/`, `Writing/`, `Narrative/`, `Design/`, `World Build/`, or attached Obsidian vaults.
     - Files like `Game-Design-Bible.md`, `Story_Canon.md`, `characters.json`, or level lists.
2. **Inspect Sibling Levels**:
   - Look for existing level folders (e.g. under `levels/`, `Graybox/`, `maps/`, or current directory).
   - Read their level files' (`.yaml` or `.json`) `notes` arrays and status files for:
     - Locked project conventions and camera rules.
     - Metric overrides or specific room proportions.
     - **Boundary connections:** Where does this level connect? (A door out of Level 1 is the entrance door to Level 2 — always carry connections into the notes.)
3. **If Context Cannot Be Found, ASK**:
   > *"I couldn't locate the narrative bible or existing level folders in the current directory. Where does the lore/story documentation for this project live, and what folder should this new level live in?"*

---

## Phase 1 — Beats Before Rooms

**The Golden Rule: Rooms are beats made physical.**
A level starts as an ordered list of story and gameplay beats, not a floor plan.

1. **Define the Numbered Spine (5–9 beats):**
   - What must happen here, in what order?
   - What does each beat require physically? (terminal, locked blast door, cover barricade, crawl vent, boss arena)
   - What dialogue or radio transmissions fire at each beat? Who speaks?
   - What state changes occur? (`has_keycard`, `alarm_tripped`, `power_restored`)
2. **Loop Beat Lines:**
   - Route the player back through previously explored space under changed conditions (calm intake becomes hostile lockdown).
   - Zigzag the calm leg so the player learns the geometry and landmark props before danger strikes.

---

## Phase 2 — Bootstrap the Level Folder

Create `<levels-dir>/<level-name>/`, copy in **all** generator scripts from this skill's `scripts/` folder (including `level_io.py` — the others import it), and start `input/level.yaml`. Level files go in `input/`; everything generated lands in `output/`:

```yaml
project: "OSL"
level: "K-67 — Research Sub-Level"
metric:
  unit_m: 1
  operative_m: 1.8
  wall: "2x3"
  door: "2x1.2"
notes:
  - "CONNECTIONS: Entrance from [Prev Level], Exit to [Next Level]."
  - "CAMERA: fixed oblique 55deg / orthographic, no rotation."
  - "GATING: Door requires Keycard from Sec Room."
rooms: []
features: []
props: []
beats: []
path: []
path_return: []
```

Requires PyYAML once per machine: `python -m pip install pyyaml` (on Windows, `py` also works)

**For every field (rooms, features, doors, props, beats, path, speakers), read `SCHEMA.md` for the complete spec.**

---

## Phase 3 — The Metric & Camera Discipline

### The Metric (Never Negotiate It)
- **1 grid cell = 1 meter.**
- Standard operative: 1.8 m tall, 0.6 m shoulder width.
- Tight corridor: 2–3 m wide. Spacious hall: 6–10 m wide.
- Standard door: 2 m high × 1.2 m wide.
- **Origin top-left: x goes right, y goes down (north = up-screen).**

### Camera Discipline (Fixed Oblique / Top-Down)
- **North walls are display walls:** their south face points at the camera. Mount readable displays, terminals, key signage, and windows there.
- **South walls are dumb walls:** keep critical interactables off them.
- **Pokemon-counter pattern:** free-standing interactables face south with standing room below.
- **Reveals annex off the north wall:** rooms the player looks into from outside sit along the north wall.

---

## Phase 4 — Coarse, Then Carve (The Design Loop)

1. **Macro Blockout:** define `rooms`, main `beats`, and `path`.
2. **Walk It Verbally:** step through the level in conversation — what does the player see, hear, what does the radio say? Every physical noun becomes a measured block.
3. **Check Connectivity:** follow `path` — every time it crosses a wall, there must be a `door` or `opening` there.
4. **Interrogate Every Space:** does this room have a beat? If not, give it one or cut it. Does this prop have narrative purpose?
5. **Validate & Bake** (from the level folder):
   ```bash
   python validate.py          # check for errors before rendering
   python render_map.py        # to-scale 2D blueprint SVG        -> output/<name>-map.svg
   python gen_walkthrough.py   # 3D interactive walkthrough       -> output/<name>-walk.html
   python gen_blender.py       # OBJ for Blender/Unity import      -> output/<name>_graybox.obj
   ```
   With several level files in one folder, name the one you want: `python gen_walkthrough.py lvl2.yaml`.

   Validators run automatically before generation; errors stop generation unless `--force` is passed. Read warnings — they catch common mistakes.

   (On Windows, `py` also works in place of `python`)

---

## Phase 5 — Interactive Walkthrough Verification Checklist

Open the walkthrough in a browser:
- [ ] **Scale & Spacing:** do hallways feel claustrophobic or roomy as intended?
- [ ] **Connectivity:** can you physically walk the whole `path`? Gated doors open when their flag is set?
- [ ] **Camera Sightlines:** switch to oblique (`V`). Can all interactables and doors be seen?
- [ ] **Story & Dialogue Flow:** walk beats 1 to N. Does dialogue trigger at the right moment?
- [ ] **Dialogue Rhythm:** are lines punchy? Does reading time match walking distance to the next objective?
- [ ] **State Gating:** try locked doors before getting keys to confirm `denied_dialogue` plays.
- [ ] **Comm Log (`H`):** does the full transcript read as a coherent scene?
