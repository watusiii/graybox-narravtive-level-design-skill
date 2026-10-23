# Level File Schema Reference

Complete field-by-field schema for `.yaml` and `.json` level files.

## Top-Level Structure

```yaml
project: "Game Title"           # Project name (displays in HUD, map header)
level: "Level Name"              # Level identifier
metric:                          # Spatial metric (locked, don't change per-level)
  unit_m: 1                      # 1 grid cell = 1 meter
  operative_m: 1.8               # Player character height in meters
  wall: "2x3"                    # Standard wall thickness x height (not parsed, doc only)
  door: "2x1.2"                  # Standard door dimensions (not parsed, doc only)
speakers:                        # Speaker colors for comm-log (optional)
  speakerId:
    color: "#hexcolor"           # CSS color for this speaker's log entries
notes: []                        # Free-form design notes (array of strings)
rooms: []                        # Room rectangles (see below)
features: []                     # Footprints and architecture (see below)
props: []                        # Point interactables (see below)
beats: []                        # Narrative spine and dialogue triggers (see below)
path: []                         # Critical path waypoints [x, y]
path_return: []                  # Return path (optional, dashed red on map)
```

---

## `rooms`

Rectangles defining the floor plan. Walls are generated from room outlines; shared edges merge into one wall. Rooms only connect through a `door` or `opening` on their shared wall — no door = solid wall.

```yaml
rooms:
  - id: "room_01"                # Unique room ID (for reference)
    label: "MAIN LAB"            # Display label (rendered on map)
    x: 0                         # Top-left corner X (meters, origin top-left)
    y: 0                         # Top-left corner Y (meters)
    w: 20                        # Width (meters)
    h: 14                        # Height (meters)
```

**Required fields:** `id`, `label`, `x`, `y`, `w`, `h`

---

## `features`

Footprints and architectural elements. Types:

### `block` — Solid footprints

Crates, consoles, tables, machinery. The workhorse element for physical objects.

```yaml
- type: "block"
  label: "CONSOLE"               # Display label (optional)
  x: 4.0                         # Top-left corner X
  y: 6.0                         # Top-left corner Y
  w: 1.5                         # Width
  h: 0.8                         # Depth
  height: 1.2                    # Height in meters (default: 1.2)
  y0: 0.0                        # Height off floor (default: 0.0 = ground level)
  danger: false                  # Render in hazard red (default: false)
```

**Required:** `type`, `x`, `y`, `w`, `h`
**Optional:** `label`, `height`, `y0`, `danger`

### `door` — Doors and airlocks

Doors cut openings in walls and can be gated by state flags.

**Vertical door** (on north/south wall):
```yaml
- type: "door"
  label: "AIRLOCK"
  x: 16                          # Wall line (vertical wall at this X)
  y: 7                           # Door starts here along the wall
  h: 2                           # Door opening width (spans y..y+h)
  danger: false
  opens_when:                    # State flags required to open (optional)
    keycard_obtained: true
```

**Horizontal door** (on east/west wall):
```yaml
- type: "door"
  label: "BLAST DOOR"
  x: 10                          # Door starts here along the wall
  y: 8                           # Wall line (horizontal wall at this Y)
  w: 3                           # Door opening width (spans x..x+w)
  opens_when:
    power_restored: true
```

**Required:** `type`, `x`, `y`, and either `h` (vertical) or `w` (horizontal)
**Optional:** `label`, `danger`, `opens_when`

Doors are **solid** unless they have `opens_when` — once the state matches, the door vanishes and becomes walkable.

### `opening` — Open gaps

Open gap in a wall, nothing drawn (e.g., an alcove open to a hallway).

```yaml
- type: "opening"
  label: "ALCOVE MOUTH"
  x: 24                          # Wall line
  y: 16.5                        # Opening starts here
  h: 3                           # Opening width (vertical) or w for horizontal
```

**Required:** `type`, `x`, `y`, and either `h` or `w`

### `wreck` — Rubble or overhead gantries

```yaml
- type: "wreck"
  label: "COLLAPSED DEBRIS"
  x: 10
  y: 12
  w: 4
  h: 3
  danger: true
```

If the label contains "GANTRY", it renders as an overhead rail; otherwise, rubble.

### `vent` / `grate` — Ducts and crawlspaces

```yaml
- type: "vent"
  label: "AIR DUCT"
  x: 21
  y: 6.4
  w: 2
  h: 0.9
  danger: true
```

Vents are wall-mounted ducts. Grates crossing a horizontal wall punch a 2m crawl hole.

---

## `props`

Point interactables or markers. Rendered as small cylinders in the walkthrough.

```yaml
props:
  - label: "KEYCARD"
    x: 12                        # Position X
    y: 6                         # Position Y
    danger: false
```

**Required:** `label` (or omit for generic marker), `x`, `y`
**Optional:** `danger`

---

## `beats`

Narrative spine and dialogue triggers. Beats are the story skeleton; rooms are beats made physical.

```yaml
beats:
  - n: 1                         # Beat number (sequential: 1, 2, 3, ...)
    x: 4.0                       # Trigger position X
    y: 12.0                      # Trigger position Y
    label: "Arrival & Orientation"          # Beat name
    objective: "Report to the central console."  # HUD objective text
    trigger_type: "auto"         # "auto" = fires on entering radius, "interact" = requires [E]
    action_label: "ACCESS TERMINAL"         # Interact prompt text (if trigger_type: "interact")
    radius: 3.0                  # Trigger radius in meters (default: 2.5)
    requires_state:              # State flags required to activate (optional)
      has_keycard: true
    denied_dialogue:             # Lines if player interacts before requires_state is met (optional)
      - speaker: "terminal"
        name: "TERMINAL"
        channel: "SYSTEM"
        text: "Access denied. Clearance required."
    set_state:                   # State flags set when dialogue completes
      entered_lab: true
    dialogue:                    # Dialogue lines (array)
      - speaker: "commander"     # Speaker ID (matches speakers: and portraits/commander.png if present)
        name: "COMMANDER VANCE"  # Display name
        channel: "TACTICAL COMM" # Comm channel label
        text: "Operative, you are on site. Maintain radio silence."
    danger: false                # Hazard red rendering
```

**Required:** `n`, `x`, `y`, `label`
**Optional:** `objective`, `trigger_type`, `action_label`, `radius`, `requires_state`, `denied_dialogue`, `set_state`, `dialogue`, `danger`

### State Gating

Every flag starts unset (`false`). Beats set flags via `set_state`. Every flag set by any beat shows up as a HUD badge automatically. Flags set by `danger: true` beats glow red.

---

## `path` & `path_return`

Waypoints tracing the critical path through the level. `path` is the forward route (dashed gold on map); `path_return` is the backtrack leg (dashed red).

```yaml
path:
  - [10, 2.5]                    # [x, y] in meters
  - [3.5, 7.0]
  - [14.6, 8.0]
```

---

## `speakers`

Optional top-level map defining speaker colors for the comm-log transcript.

```yaml
speakers:
  miller:
    color: "#e7dfc9"             # Pale amber
  kael:
    color: "#e8b23a"             # Gold
  laura:
    color: "#68d391"             # Green
  terminal:
    color: "#9a9788"             # Dim gray
```

If not defined, all speakers default to gold (`#e8b23a`).

---

## Coordinate System

- **Origin:** Top-left (x goes right, y goes down)
- **Units:** 1 grid cell = 1 meter
- **North = up-screen** (low Y values are "north")

---

## Camera Discipline (Fixed Oblique / Top-Down)

- **North walls are display walls:** Their south face points at the camera. Mount all readable displays, terminals, key signage, and windows there.
- **South walls are dumb walls:** Avoid critical interactables on south walls where geometry blocks the view.
- **Pokemon-counter pattern:** Free-standing interactables (kiosks, desks, bodies) face south with standing room below them.
- **Reveals annex off the north wall:** Rooms the player looks into from the outside should sit along the north wall.

---

## Validation

Run `python validate.py` (or `py` on Windows) to catch errors before rendering:

- Path crosses wall with no door/opening
- Beat `requires_state` flag never set by earlier beat
- Door `opens_when` flag never set by any beat
- Duplicate or non-sequential beat numbers
- Beat/prop/path point outside every room
- Missing required fields

Warnings:
- Interact beat with `requires_state` but no `denied_dialogue`
- Room with no beats in it
