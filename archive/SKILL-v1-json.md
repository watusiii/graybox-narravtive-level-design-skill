---
name: graybox-level-design
description: Generate a NEW game level from scratch by conversation, data-first. Use when the user wants to create, generate, start, or block out a new level, room, area, or map ("make a new level", "generate the next level", "design the next area", "block out the research lab", "new graybox", "walkthrough for Phase"). Works for any narrative, top-down, tactical, or isometric game (e.g. Phase, OSL Shooter). Bootstraps a level folder with its own JSON source of truth and generators that render a 2D map, a 3D walkable browser graybox with tactile dialogue, and an engine-ready OBJ.
---

# Graybox Level Design — Data-First Narrative Level Generator

Levels are born as **data**: each level is a folder with one JSON source of truth (`level.json` or `vslice.json`); generators render the 2D SVG map, the interactive 3D browser walkthrough with in-world dialogue, and the 3D OBJ mesh. The conversation IS the design tool.

---

## Phase 0 — Context Discovery Before Geometry

Never assume hardcoded paths. Before designing or generating geometry:

1. **Check Current Working Directory First**:
   - Inspect the current directory and its parent/child subtrees for project documentation, design bibles, lore notes, character manifests, or existing level folders:
     - Folders like `docs/`, `Documentation/`, `Writing/`, `Narrative/`, `Design/`, `World Build/`, or attached Obsidian vaults.
     - Files like `Game-Design-Bible.md`, `Story_Canon.md`, `characters.json`, or level lists.
2. **Inspect Sibling Levels**:
   - Look for existing level folders (e.g. under `levels/`, `Graybox/`, `maps/`, or current directory).
   - Read their JSON `notes` arrays and status files for:
     - Locked project conventions and camera rules.
     - Metric overrides or specific room proportions.
     - **Boundary connections:** Where does this level connect? (A door out of Level 1 is the entrance door to Level 2—always carry connections into the notes).
3. **If Context Cannot Be Found, ASK**:
   - If no design docs, narrative bible, or target level directory can be located automatically:
     > *"I couldn't locate the narrative bible or existing level folders in the current directory. Where does the lore/story documentation for this project live, and what folder should this new level live in?"*

---

## Phase 1 — Beats Before Rooms

**The Golden Rule: Rooms are beats made physical.** 
A level starts as an ordered list of story and gameplay beats, not a floor plan.

1. **Define the Numbered Spine (5–9 beats):**
   - What must happen here, in what order?
   - What does each beat require physically? (e.g., terminal, locked blast door, cover barricade, crawl vent, boss arena).
   - What dialogue or radio transmissions fire at each beat? Who speaks?
   - What state changes occur? (e.g., `has_keycard`, `alarm_tripped`, `power_restored`).
2. **Loops Beat Lines:**
   - Route the player back through previously explored space under changed conditions (e.g. calm intake becomes hostile lockdown).
   - Zigzag the calm leg so the player naturally learns the geometry and landmark props before danger strikes.

---

## Phase 2 — Bootstrap the Level Folder

Create the level folder `<levels-dir>/<level-name>/` (or use the current working directory if already inside the level folder), copy in the generator scripts from this skill's `scripts/` directory, and initialize `level.json`:

```json
{
  "project": "<Game Title, e.g. Phase or OSL>",
  "level": "<CODE> — <Level Name>",
  "metric": {
    "unit_m": 1,
    "operative_m": 1.8,
    "wall": "2x3",
    "door": "2x1.2"
  },
  "notes": [
    "CONNECTIONS: Entrance from [Prev Level], Exit to [Next Level].",
    "CAMERA: fixed oblique 55deg / orthographic, no rotation.",
    "GATING: Door requires Keycard from Sec Room."
  ],
  "rooms": [],
  "features": [],
  "props": [],
  "beats": [],
  "path": [],
  "path_return": []
}
```

### The JSON Schema:
* **`rooms`**: `[{ "id": "lab_01", "label": "MAIN LAB", "x": 0, "y": 0, "w": 20, "h": 14 }]` (measured in meters).
* **`features`**: Footprints and architectural elements:
  * `type: "block"` — Solid physical footprints (crates, consoles, tables, machinery). Workhorse element.
  * `type: "door"` — Doors and airlocks (`x` is wall position, `h` is door opening width).
  * `type: "wreck"` — Overhead gantry, collapsed rubble, or dashed ceiling rails.
  * `type: "vent"` / `type: "grate"` — Ducts, grates, crawlspaces.
  * `"danger": true` — Highlights element in hazard red.
* **`props`**: Point interactables or markers `[{ "label": "KEYCARD", "x": 12, "y": 6, "danger": false }]`.
* **`beats`**: Narrative spine and dialogue triggers:
  ```json
  {
    "n": 1,
    "x": 4.0,
    "y": 12.0,
    "label": "Arrival & Orientation",
    "objective": "Report to the central console.",
    "trigger_type": "auto",
    "radius": 3.0,
    "requires_state": {},
    "set_state": { "entered_lab": true },
    "dialogue": [
      {
        "speaker": "commander",
        "name": "COMMANDER VANCE",
        "channel": "TACTICAL COMM",
        "text": "Operative, you are on site. Maintain radio silence until the perimeter is secure."
      }
    ]
  }
  ```
  * `trigger_type`: `"auto"` (fires on entering radius) or `"interact"` (prompts `[E] <action_label>`).
  * `action_label`: Custom prompt text, e.g. `"ACCESS TERMINAL"`, `"PICK UP KEYCARD"`, `"PRY HATCH"`.
  * `requires_state`: Flags required to activate (e.g. `{"has_key": true}`).
  * `denied_dialogue`: Fallback lines if player interacts before meeting `requires_state` (e.g. *"Locked. Maglock requires clearance badge."*).
  * `set_state`: State updates applied when dialogue completes.
* **`path`** & **`path_return`**: `[[x, y], ...]` waypoints tracing the critical path through the level.

---

## Phase 3 — The Metric & Camera Discipline

### The Metric (Never Negotiate It)
* **1 grid cell = 1 meter.**
* Standard operative: 1.8 m tall, 0.6 m shoulder width.
* Tight corridor: 2–3 m wide. Spacious hall: 6–10 m wide.
* Standard door: 2 m high × 1.2 m wide.
* **Origin top-left: x goes right, y goes down (north = up-screen).**

### Camera Discipline (Fixed Oblique / Top-Down)
* **North walls are display walls:** Their south face points directly at the camera. Mount all readable displays, terminals, key signage, and windows there.
* **South walls are dumb walls:** Avoid putting critical interactables on south walls where geometry blocks the view.
* **Pokemon-counter pattern:** Free-standing interactables (kiosks, desks, bodies) face south with standing room below them.
* **Reveals annex off the north wall:** Rooms the player looks into from the outside should sit along the north wall.

---

## Phase 4 — Coarse, Then Carve (The Design Loop)

1. **Macro Blockout:** Define `rooms`, main `beats`, and `path`.
2. **Walk It Verbally:** Walk through the level step-by-step in conversation:
   - What does the player see upon entering?
   - What sound plays? What line does the radio crackle with?
   - Every physical noun mentioned becomes a measured block in the JSON.
3. **Interrogate Every Space:**
   - Does this room have a beat? If not, give it one or cut it.
   - Does this prop have narrative purpose? (e.g. A decorative vent becomes the escape route).
4. **Bake & Test-Walk:**
   ```bash
   py render_map.py        # Generates to-scale 2D blueprint SVG (open in browser)
   py gen_walkthrough.py   # Generates 3D interactive walkthrough (walk.html)
   py gen_blender.py       # (Optional) Generates .obj for Blender/Unity import
   ```

---

## Phase 5 — Interactive Walkthrough Verification Checklist

Open `walk.html` in a web browser to verify:
- [ ] **Scale & Spacing:** Do hallways feel claustrophobic or roomy as intended?
- [ ] **Camera Sightlines:** Switch to oblique camera (`V`). Can all interactables and doors be seen clearly?
- [ ] **Story & Dialogue Flow:** Walk through each beat (1 to N). Does the dialogue trigger at the right moment?
- [ ] **Dialogue Rhythm:** Are lines punchy? Does the reading time match the walking distance to the next objective?
- [ ] **State Gating:** Try locked doors before getting keys/badges to ensure `denied_dialogue` plays properly.
- [ ] **Comm Log (`[H]`):** Does the full transcript read as a coherent story scene?
