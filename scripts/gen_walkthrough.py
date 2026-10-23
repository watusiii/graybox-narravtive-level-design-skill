"""
gen_walkthrough.py — bake a level file (.yaml or .json) into walk.html,
a walkable Three.js graybox with tactile Codec dialogue.

    python gen_walkthrough.py               # auto-picks the level file in this folder
    python gen_walkthrough.py lvl2.yaml     # or name one

Reads from input/, writes to output/. Then open the .html in a browser. Re-run after every level edit.
Walls, floor, HUD flags and beat count all come from the level file — nothing level-specific is hardcoded.
Runs validate.py first; errors stop generation unless --force is passed.
"""
import json, os, base64, sys
from level_io import load_level_data, find_level_file, build_walls, floor_bounds, output_dir
from validate import validate_level

HERE = os.path.dirname(os.path.abspath(__file__))

def find_portraits_dir():
    for c in (os.path.join(HERE, "input", "portraits"),
              os.path.join(HERE, "portraits"),
              os.path.join(HERE, "..", "portraits"),
              os.path.join(HERE, "..", "..", "portraits")):
        if os.path.isdir(c):
            return os.path.abspath(c)
    return None

def load_portraits():
    pdir = find_portraits_dir()
    res = {}
    if not pdir:
        return res
    for f in os.listdir(pdir):
        ext = os.path.splitext(f)[1].lower()
        if ext in (".png", ".jpg", ".jpeg"):
            key = os.path.splitext(f)[0].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            try:
                with open(os.path.join(pdir, f), "rb") as fh:
                    res[key] = f"data:{mime};base64,{base64.b64encode(fh.read()).decode('utf-8')}"
            except Exception as e:
                print(f"WARNING: portrait {f} skipped — {e}")
    return res

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__PROJECT_TITLE__ // __LEVEL_TITLE__</title>
<style>
  * { box-sizing: border-box; user-select: none; }
  body { margin:0; overflow:hidden; background:#141410; font-family:'Cascadia Mono', Consolas, ui-monospace, monospace; color:#e7dfc9; }

  #hud { position:fixed; top:14px; left:16px; color:#9a9788; font-size:12px; letter-spacing:1px;
         background:rgba(20,20,16,0.85); padding:12px 16px; border:1px solid #34342a; border-radius:4px;
         backdrop-filter:blur(4px); z-index:10; }
  #hud b { color:#e8b23a; }
  .hud-btn { display:inline-block; margin-top:8px; padding:3px 8px; font-size:11px; background:#26261f;
             border:1px solid #484436; color:#e8b23a; cursor:pointer; border-radius:2px; }
  .hud-btn:hover { background:#34342a; color:#fff; }

  #objective-hud { position:fixed; top:14px; right:16px; color:#e7dfc9; font-size:12px; letter-spacing:1px;
                   background:rgba(20,20,16,0.88); padding:14px 18px; border:1px solid #34342a; border-radius:4px;
                   max-width:380px; backdrop-filter:blur(4px); z-index:10; }
  #obj-title { color:#9a9788; font-size:10px; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:4px; display:flex; justify-content:space-between; gap:12px; }
  #obj-status { color:#e8b23a; font-weight:700; font-size:13px; line-height:1.4; }
  #state-badges { margin-top:10px; display:flex; flex-wrap:wrap; gap:6px; font-size:10px; }
  .badge { padding:3px 7px; background:#1e1e18; border:1px solid #34342a; border-radius:2px; color:#706e62; }
  .badge.active { border-color:#e8b23a; color:#e8b23a; background:rgba(232,178,58,0.12); }
  .badge.danger.active { border-color:#ff3b30; color:#ff6a60; background:rgba(255,59,48,0.15); }

  #interact-prompt { position:fixed; top:65%; left:50%; transform:translate(-50%, -50%);
                     color:#141410; background:#e8b23a; font-size:14px; font-weight:700; letter-spacing:1.5px;
                     padding:8px 20px; border-radius:3px; box-shadow:0 0 20px rgba(232,178,58,0.4);
                     display:none; pointer-events:none; z-index:20; text-transform:uppercase; animation:pulse 1s infinite alternate; }
  @keyframes pulse { from { opacity:0.85; transform:translate(-50%, -50%) scale(0.98); } to { opacity:1; transform:translate(-50%, -50%) scale(1.02); } }

  #codec-window { position:fixed; bottom:22px; left:50%; transform:translateX(-50%); width:calc(100% - 40px);
                  max-width:840px; background:rgba(18,18,14,0.96); border:1px solid #484436; border-radius:4px;
                  box-shadow:0 0 25px rgba(0,0,0,0.8), 0 0 15px rgba(232,178,58,0.1); display:none; z-index:30;
                  overflow:hidden; backdrop-filter:blur(6px); }
  #codec-header { background:#1b1b15; border-bottom:1px solid #34342a; padding:6px 14px; display:flex;
                  justify-content:space-between; align-items:center; font-size:11px; letter-spacing:1.5px; }
  .rec-indicator { display:flex; align-items:center; gap:6px; color:#ff3b30; font-weight:700; }
  .rec-dot { width:8px; height:8px; border-radius:50%; background:#ff3b30; animation:blink 0.8s infinite alternate; }
  @keyframes blink { from { opacity:0.3; } to { opacity:1; } }
  #channel-tag { color:#e8b23a; font-weight:700; }
  #beat-tag { color:#9a9788; }

  #codec-body { display:grid; grid-template-columns:130px 1fr; gap:18px; padding:18px; align-items:start; }
  #portrait-col { display:flex; flex-direction:column; align-items:center; gap:8px; }
  #portrait-frame { width:110px; height:110px; background:#141410; border:2px solid #484436;
                    border-radius:3px; overflow:hidden; position:relative; display:flex; align-items:center; justify-content:center; }
  #portrait-img { width:100%; height:100%; object-fit:cover; display:block; }
  #portrait-frame::after { content:""; position:absolute; inset:0; pointer-events:none;
                           background:repeating-linear-gradient(0deg, rgba(0,0,0,0.2) 0px, rgba(0,0,0,0.2) 1px, transparent 1px, transparent 2px); }
  #speaker-badge { font-size:11px; font-weight:700; color:#e8b23a; text-align:center; letter-spacing:1px; line-height:1.2; }

  #dialogue-col { display:flex; flex-direction:column; justify-content:space-between; min-height:110px; }
  #dialogue-text { font-size:15px; line-height:1.65; color:#f0ece1; white-space:pre-wrap; word-break:break-word; }
  #codec-footer { margin-top:14px; display:flex; justify-content:space-between; align-items:center;
                  font-size:11px; color:#9a9788; border-top:1px dashed #2e2e26; padding-top:8px; }
  #next-prompt { color:#e8b23a; font-weight:700; letter-spacing:1px; cursor:pointer; }
  #next-prompt:hover { color:#fff; text-shadow:0 0 8px #e8b23a; }

  #log-modal { position:fixed; inset:40px; background:rgba(18,18,14,0.98); border:1px solid #484436;
               border-radius:6px; z-index:100; display:none; flex-direction:column; padding:24px; box-shadow:0 0 40px #000; }
  #log-header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #34342a;
                padding-bottom:12px; margin-bottom:16px; font-size:14px; color:#e8b23a; letter-spacing:1.5px; }
  #log-list { flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:16px; padding-right:12px; }
  .log-entry { border-left:2px solid #484436; padding-left:12px; font-size:13px; line-height:1.5; }
  __SPEAKER_STYLES__
  .log-speaker { font-weight:700; color:#e8b23a; margin-bottom:2px; font-size:11px; letter-spacing:1px; }

  #cross { position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); color:#e8b23a; font-size:16px; pointer-events:none; }
</style>
</head>
<body>

<div id="hud">
  <b>__PROJECT_TITLE__ // __LEVEL_TITLE__</b><br>
  click window to capture mouse<br>
  <b>WASD</b> move &middot; <b>Shift</b> run<br>
  <b>V</b> camera: first-person / game oblique<br>
  <b>scroll</b> zoom in oblique cam<br>
  <b>E</b> or <b>Space</b> interact / advance dialogue<br>
  <button class="hud-btn" onclick="toggleLog()">[H] COMM LOG</button>
  <button class="hud-btn" onclick="resetToSpawn()">[R] RESET</button>
</div>

<div id="objective-hud">
  <div id="obj-title">
    <span>TACTICAL OBJECTIVE</span>
    <span id="beat-num"></span>
  </div>
  <div id="obj-status"></div>
  <div id="state-badges"></div>
</div>

<div id="interact-prompt">[E] INTERACT</div>

<div id="codec-window">
  <div id="codec-header">
    <div class="rec-indicator"><span class="rec-dot"></span><span>LIVE TRANSMISSION</span></div>
    <div id="channel-tag">[ COMM-LINK ]</div>
    <div id="beat-tag">BEAT 01</div>
  </div>
  <div id="codec-body">
    <div id="portrait-col">
      <div id="portrait-frame">
        <img id="portrait-img" src="" alt="Portrait">
      </div>
      <div id="speaker-badge"></div>
    </div>
    <div id="dialogue-col">
      <div id="dialogue-text">...</div>
      <div id="codec-footer">
        <div id="line-counter"></div>
        <div id="next-prompt" onclick="advanceDialogue()">[ SPACE / E ] NEXT ►</div>
      </div>
    </div>
  </div>
</div>

<div id="log-modal">
  <div id="log-header">
    <span>__PROJECT_TITLE__ TRANSMISSION LOG</span>
    <button class="hud-btn" onclick="toggleLog()">CLOSE [ESC]</button>
  </div>
  <div id="log-list"></div>
</div>

<div id="cross">+</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const L = __LEVEL_JSON__;
const WALLS = __WALLS_JSON__;
const FLOOR = __FLOOR_JSON__;   // [x, z, w, d]
const PORTRAITS = __PORTRAITS_JSON__;
const TOTAL = L.beats.length;
const pad2 = n => String(n).padStart(2, '0');

const TERMINAL_ICON = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect width="120" height="120" fill="%23141410"/><rect x="15" y="20" width="90" height="70" rx="4" fill="%231e1e18" stroke="%23e8b23a" stroke-width="3"/><line x1="28" y1="42" x2="60" y2="42" stroke="%23e8b23a" stroke-width="4"/><line x1="28" y1="58" x2="84" y2="58" stroke="%239a9788" stroke-width="3"/><line x1="28" y1="72" x2="72" y2="72" stroke="%239a9788" stroke-width="3"/><circle cx="90" cy="30" r="3" fill="%23ff3b30"/></svg>';

const WALL_H = 4, EYE = 1.7, R = 0.35;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x141410);
scene.fog = new THREE.Fog(0x141410, 30, 75);

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
document.body.appendChild(renderer.domElement);

let camDist = 12;
const cam = new THREE.PerspectiveCamera(72, innerWidth/innerHeight, 0.05, 200);
const ocam = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 200);
function syncOrtho(){
  const a = innerWidth/innerHeight, h = camDist;
  ocam.left = -h*a/2; ocam.right = h*a/2; ocam.top = h/2; ocam.bottom = -h/2;
  ocam.updateProjectionMatrix();
}
addEventListener('resize', ()=>{ cam.aspect=innerWidth/innerHeight; cam.updateProjectionMatrix(); syncOrtho(); renderer.setSize(innerWidth,innerHeight); });

scene.add(new THREE.HemisphereLight(0xdad6c8, 0x24241e, 0.95));
const sun = new THREE.DirectionalLight(0xfff2d8, 0.55); sun.position.set(10,22,6); scene.add(sun);

const M = {
  wall:  new THREE.MeshLambertMaterial({color:0x6e6e68}),
  block: new THREE.MeshLambertMaterial({color:0x93938a}),
  danger:new THREE.MeshLambertMaterial({color:0xa04038}),
  amber: new THREE.MeshLambertMaterial({color:0xc08a2e}),
  red:   new THREE.MeshLambertMaterial({color:0xb03028}),
  dark:  new THREE.MeshLambertMaterial({color:0x44443e})
};

// 1m grid floor sized to the rooms
const gc = document.createElement('canvas'); gc.width = gc.height = 64;
const g = gc.getContext('2d');
g.fillStyle = '#22221b'; g.fillRect(0,0,64,64);
g.strokeStyle = '#2e2e24'; g.lineWidth = 2; g.strokeRect(0,0,64,64);
const gt = new THREE.CanvasTexture(gc);
gt.wrapS = gt.wrapT = THREE.RepeatWrapping; gt.repeat.set(FLOOR[2], FLOOR[3]);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(FLOOR[2], FLOOR[3]), new THREE.MeshLambertMaterial({map:gt}));
floor.rotation.x = -Math.PI/2; floor.position.set(FLOOR[0]+FLOOR[2]/2, 0, FLOOR[1]+FLOOR[3]/2); scene.add(floor);

const colliders = [];
function box(x, z, w, d, h, mat, y0=0, collide=true){
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x+w/2, y0+h/2, z+d/2); scene.add(m);
  if (collide){
    const c = {x1:x, x2:x+w, z1:z, z2:z+d, y0:y0, y1:y0+h, off:false};
    colliders.push(c); m.userData.collider = c;
  }
  return m;
}

// walls: precomputed in Python from room outlines + door/opening/grate holes
for (const w of WALLS) box(w.x, w.z, w.w, w.d, w.h, M.wall, w.y0);

function sprite(text, color, x, y, z, s=1){
  const c = document.createElement('canvas'); c.width = 512; c.height = 96;
  const ctx = c.getContext('2d');
  ctx.font = '600 38px Cascadia Mono, Consolas, monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = color;
  ctx.shadowColor = '#000'; ctx.shadowBlur = 8;
  ctx.fillText(text, 256, 48);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c), depthTest:false}));
  sp.scale.set(4.2*s, 0.8*s, 1); sp.position.set(x, y, z); scene.add(sp);
  return sp;
}

function heightFor(f){
  return f.height || 1.2;  // explicit height, or default
}

function y0For(f){
  return f.y0 || 0.0;  // explicit y0 (height off floor), or ground level
}

const gatedDoors = [];   // doors with opens_when: hidden + walkable once the state matches
for (const f of L.features){
  if (f.type === 'block'){
    const h = heightFor(f);
    const y0 = y0For(f);
    box(f.x, f.y, f.w, f.h, h, f.danger ? M.danger : M.block, y0);
    if (f.label) sprite(f.label, f.danger ? '#ff6a60' : '#e7dfc9', f.x+f.w/2, y0+h+0.55, f.y+f.h/2, 0.85);
  } else if (f.type === 'wreck'){
    if ((f.label||'').toUpperCase().includes('GANTRY')){
      box(f.x, f.y, f.w, f.h, 0.25, M.dark, 3.1, false);
      box(f.x+f.w*0.35, f.y+f.h*0.2, 0.15, 0.15, 0.8, M.dark, 2.3, false);
      sprite(f.label, '#9a9788', f.x+f.w/2, 3.9, f.y+f.h/2, 0.8);
    } else {
      box(f.x, f.y, f.w, f.h, 2.8, M.dark);
      if (f.label) sprite(f.label, '#e8b23a', f.x+f.w/2, 3.5, f.y+f.h/2);
    }
  } else if (f.type === 'door'){
    let mesh, label;
    if (f.h){  // vertical door
      const isW = f.x < 1;
      mesh = box(isW ? -0.17 : f.x-0.17, f.y, 0.34, f.h, 3.4, f.danger ? M.red : M.amber);
      label = f.label ? sprite(f.label, f.danger ? '#ff6a60' : '#e8b23a', isW ? 0.6 : f.x-0.6, 3.7, f.y+f.h/2) : null;
    } else if (f.w){  // horizontal door
      const isN = f.y < 1;
      mesh = box(f.x, isN ? -0.17 : f.y-0.17, f.w, 0.34, 3.4, f.danger ? M.red : M.amber);
      label = f.label ? sprite(f.label, f.danger ? '#ff6a60' : '#e8b23a', f.x+f.w/2, 3.7, isN ? 0.6 : f.y-0.6) : null;
    }
    if (f.opens_when && mesh) gatedDoors.push({f, mesh, label});
  } else if (f.type === 'vent'){
    box(f.x, f.y, f.w, 0.3, 0.9, M.red, 2.6, false);
    sprite(f.label || 'VENT', '#ff6a60', f.x+f.w/2, 3.9, f.y+0.15, 0.8);
  } else if (f.type === 'grate'){
    sprite(f.label || 'GRATE', '#e8b23a', f.x+f.w/2, 2.5, f.y+f.h/2, 0.8);
  }
}

for (const p of L.props){
  const mat = p.danger ? M.danger : M.amber;
  const m = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 1.0, 10), mat);
  m.position.set(p.x, 0.5, p.y); scene.add(m);
  if (p.label) sprite(p.label, p.danger ? '#ff6a60' : '#e7dfc9', p.x, 1.8, p.y, 0.85);
}

const beatRings = [];
for (const b of L.beats){
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.45, 0.65, 24),
    new THREE.MeshBasicMaterial({color: b.danger ? 0xff3b30 : 0xe8b23a, side:THREE.DoubleSide}));
  ring.rotation.x = -Math.PI/2; ring.position.set(b.x, 0.03, b.y); scene.add(ring);
  sprite(String(b.n), b.danger ? '#ff6a60' : '#e8b23a', b.x, 1.1, b.y, 0.6);
  beatRings.push({beat: b, ring: ring});
}

function pathLine(pts, color){
  if (!pts || pts.length < 2) return;
  const geo = new THREE.BufferGeometry().setFromPoints(pts.map(p => new THREE.Vector3(p[0], 0.06, p[1])));
  const line = new THREE.Line(geo, new THREE.LineDashedMaterial({color:color, dashSize:0.35, gapSize:0.3}));
  line.computeLineDistances(); scene.add(line);
}
pathLine(L.path, 0xe8b23a);
pathLine(L.path_return, 0xff3b30);

// Player
const r0 = L.rooms[0] || {x:0, y:0, w:2, h:2};
const spawn = L.beats[0] ? {x:L.beats[0].x, z:L.beats[0].y} : {x:r0.x+r0.w/2, z:r0.y+r0.h/2};
let px = spawn.x, pz = spawn.z, yaw = Math.PI/2, pitch = -0.05;
const avatar = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 1.8, 12),
  new THREE.MeshLambertMaterial({color:0xe8b23a}));
avatar.visible = false; scene.add(avatar);

let oblique = false;
const keys = {};
function resetToSpawn(){ px = spawn.x; pz = spawn.z; yaw = Math.PI/2; }

// --- STORY / DIALOGUE ENGINE ---
// Every flag starts unset; beats set them via set_state.
const storyState = { completedBeats: new Set() };

// HUD flags = every flag any beat sets, in story order. Flags set by danger beats glow red.
const FLAGS = [];
for (const b of L.beats){
  for (const k of Object.keys(b.set_state || {})){
    if (!FLAGS.find(f => f.key === k)) FLAGS.push({key:k, danger:!!b.danger});
  }
}
const badgeBox = document.getElementById('state-badges');
for (const f of FLAGS){
  const el = document.createElement('span');
  el.className = 'badge' + (f.danger ? ' danger' : '');
  el.textContent = f.key.replace(/^has_/, '').replace(/_/g, ' ').toUpperCase();
  f.el = el; badgeBox.appendChild(el);
}

let activeDialogue = null;
let currentLineIdx = 0;
let transcriptHistory = [];

const codecWin = document.getElementById('codec-window');
const channelTag = document.getElementById('channel-tag');
const beatTag = document.getElementById('beat-tag');
const portraitImg = document.getElementById('portrait-img');
const speakerBadge = document.getElementById('speaker-badge');
const dialogueText = document.getElementById('dialogue-text');
const lineCounter = document.getElementById('line-counter');
const interactPrompt = document.getElementById('interact-prompt');
const objStatus = document.getElementById('obj-status');
const beatNum = document.getElementById('beat-num');

function checkRequirements(req){
  if (!req) return true;
  for (const [k, v] of Object.entries(req)){
    if ((storyState[k] ?? false) !== v) return false;
  }
  return true;
}

function refreshDoors(){
  for (const d of gatedDoors){
    const open = checkRequirements(d.f.opens_when);
    d.mesh.visible = !open;
    if (d.mesh.userData.collider) d.mesh.userData.collider.off = open;
  }
}

function updateHUD(){
  for (const f of FLAGS){
    f.el.classList.toggle('active', storyState[f.key] === true);
  }
  refreshDoors();
}

function setObjective(b){
  if (!b) return;
  objStatus.textContent = b.objective || b.label || '';
  beatNum.textContent = `BEAT ${pad2(b.n)} / ${pad2(TOTAL)}`;
}
setObjective(L.beats[0]);
updateHUD();

function startDialogue(dialogueLines, headerChannel, beatLabel, onComplete){
  if (!dialogueLines || dialogueLines.length === 0){ if (onComplete) onComplete(); updateHUD(); return; }
  activeDialogue = { lines: dialogueLines, onComplete: onComplete };
  currentLineIdx = 0;
  channelTag.textContent = headerChannel ? `[ ${headerChannel} ]` : '[ COMM-LINK ]';
  beatTag.textContent = beatLabel || 'COMMUNICATION';
  codecWin.style.display = 'block';
  renderCurrentLine();
}

function renderCurrentLine(){
  if (!activeDialogue || currentLineIdx >= activeDialogue.lines.length) return;
  const line = activeDialogue.lines[currentLineIdx];
  const spKey = (line.speaker || '').toLowerCase();
  portraitImg.src = PORTRAITS[spKey] || TERMINAL_ICON;
  speakerBadge.textContent = line.name || (line.speaker || '').toUpperCase();
  channelTag.textContent = line.channel ? `[ ${line.channel} ]` : '[ COMM-LINK ]';
  dialogueText.textContent = line.text;
  lineCounter.textContent = `LINE ${currentLineIdx + 1} / ${activeDialogue.lines.length}`;
  transcriptHistory.push({
    speaker: line.name || (line.speaker || '').toUpperCase(),
    channel: line.channel || 'COMM',
    text: line.text,
    key: spKey
  });
}

function advanceDialogue(){
  if (!activeDialogue) return;
  currentLineIdx++;
  if (currentLineIdx < activeDialogue.lines.length){
    renderCurrentLine();
  } else {
    const cb = activeDialogue.onComplete;
    activeDialogue = null;
    codecWin.style.display = 'none';
    if (cb) cb();
    updateHUD();
  }
}

function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function toggleLog(){
  const modal = document.getElementById('log-modal');
  if (modal.style.display === 'flex'){
    modal.style.display = 'none';
  } else {
    const list = document.getElementById('log-list');
    list.innerHTML = transcriptHistory.map(entry => `
      <div class="log-entry ${esc(entry.key)}">
        <div class="log-speaker">[${esc(entry.channel)}] ${esc(entry.speaker)}:</div>
        <div>${esc(entry.text)}</div>
      </div>
    `).join('') || '<div style="color:#706e62;">No transmissions recorded yet.</div>';
    modal.style.display = 'flex';
  }
}

addEventListener('keydown', e => {
  keys[e.code] = true;
  if (e.code === 'KeyV'){
    oblique = !oblique;
    avatar.visible = oblique;
    if (oblique) document.exitPointerLock();
  }
  if (e.code === 'KeyR') resetToSpawn();
  if (e.code === 'KeyH') toggleLog();
  if (e.code === 'Escape') document.getElementById('log-modal').style.display = 'none';

  if (activeDialogue && (e.code === 'Space' || e.code === 'KeyE' || e.code === 'Enter')){
    advanceDialogue();
    e.preventDefault();
    return;
  }
  if (!activeDialogue && e.code === 'KeyE' && currentInteractBeat){
    handleBeatInteraction(currentInteractBeat);
  }
});

addEventListener('keyup', e => keys[e.code] = false);
addEventListener('wheel', e => { camDist = Math.max(5, Math.min(30, camDist + e.deltaY * 0.01)); }, {passive:true});
renderer.domElement.addEventListener('click', () => {
  if (activeDialogue) { advanceDialogue(); return; }
  if (!oblique) renderer.domElement.requestPointerLock();
});

addEventListener('mousemove', e => {
  if (document.pointerLockElement !== renderer.domElement) return;
  yaw += e.movementX * 0.0023;
  pitch = Math.max(-1.35, Math.min(1.35, pitch - e.movementY * 0.0023));
});

function collide(){
  for (const c of colliders){
    if (c.off || c.y0 > 1.6) continue;
    const nx = Math.max(c.x1, Math.min(px, c.x2));
    const nz = Math.max(c.z1, Math.min(pz, c.z2));
    const dx = px - nx, dz = pz - nz;
    const d2 = dx*dx + dz*dz;
    if (d2 < R*R){
      const d = Math.sqrt(d2) || 0.0001;
      const push = (R - d);
      px += (dx/d) * push; pz += (dz/d) * push;
    }
  }
}

function handleBeatInteraction(b){
  if (!checkRequirements(b.requires_state)){
    if (b.denied_dialogue){
      startDialogue(b.denied_dialogue, 'SECURITY ALERT', b.label, null);
    }
    return;
  }
  startDialogue(b.dialogue, b.dialogue && b.dialogue[0] && b.dialogue[0].channel, `BEAT ${pad2(b.n)} // ${b.label}`, () => {
    storyState.completedBeats.add(b.n);
    if (b.set_state) Object.assign(storyState, b.set_state);
    setObjective(L.beats.find(nb => nb.n === b.n + 1) || b);
  });
}

let currentInteractBeat = null;

setTimeout(() => {
  const b0 = L.beats[0];
  if (b0 && b0.trigger_type !== 'interact' && !storyState.completedBeats.has(b0.n)) handleBeatInteraction(b0);
}, 400);

const crossDiv = document.getElementById('cross');
const clock = new THREE.Clock();

function tick(){
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), 0.05);
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 5.2 : 2.6) * dt;

  let fx, fz;
  if (oblique){ fx = 0; fz = -1; } else { fx = Math.sin(yaw); fz = -Math.cos(yaw); }
  const rx = -fz, rz = fx;

  if (keys.KeyW){ px += fx*sp; pz += fz*sp; }
  if (keys.KeyS){ px -= fx*sp; pz -= fz*sp; }
  if (keys.KeyD){ px += rx*sp; pz += rz*sp; }
  if (keys.KeyA){ px -= rx*sp; pz -= rz*sp; }

  collide(); collide();
  avatar.position.set(px, 0.9, pz);

  if (oblique){
    const tilt = 55 * Math.PI/180, D = 25;
    syncOrtho();
    ocam.position.set(px, D*Math.sin(tilt), pz + D*Math.cos(tilt));
    ocam.lookAt(px, 0.8, pz);
    crossDiv.style.display = 'none';
  } else {
    cam.position.set(px, EYE, pz);
    cam.rotation.order = 'YXZ';
    cam.rotation.y = -yaw; cam.rotation.x = pitch;
    crossDiv.style.display = activeDialogue ? 'none' : 'block';
  }

  currentInteractBeat = null;
  let promptShown = false;
  for (const item of beatRings){
    const b = item.beat;
    const d = Math.hypot(b.x - px, b.y - pz);
    if (storyState.completedBeats.has(b.n)){
      item.ring.material.opacity = 0.35;
      item.ring.material.transparent = true;
    }
    if (d < (b.radius || 2.5) && !activeDialogue){
      if (b.trigger_type !== 'interact'){
        if (!storyState.completedBeats.has(b.n) && checkRequirements(b.requires_state)){
          handleBeatInteraction(b);
          break;
        }
      } else {
        currentInteractBeat = b;
        interactPrompt.textContent = `[ E ] ${b.action_label || 'INTERACT'}`;
        interactPrompt.style.display = 'block';
        promptShown = true;
      }
    }
  }
  if (!promptShown) interactPrompt.style.display = 'none';

  renderer.render(scene, oblique ? ocam : cam);
}
tick();
</script>
</body>
</html>
'''

def html_text(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def js_json(obj):
    # safe to drop inside <script>: no raw "</" sequences
    return json.dumps(obj).replace("</", "<\\/")

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

    for k in ("rooms", "features", "props", "beats", "path", "path_return"):
        data[k] = data.get(k) or []

    # Generate speaker-specific CSS from level's speakers map
    speakers = data.get("speakers", {})
    speaker_styles = []
    for speaker_id, props in speakers.items():
        color = props.get("color", "#e8b23a")
        speaker_styles.append(f"  .log-entry.{speaker_id} {{ border-left-color:{color}; }}")
    speaker_css = "\n".join(speaker_styles) if speaker_styles else "  /* no speakers defined */"

    html = (TEMPLATE
            .replace("__LEVEL_JSON__", js_json(data))
            .replace("__WALLS_JSON__", js_json(build_walls(data)))
            .replace("__FLOOR_JSON__", js_json(list(floor_bounds(data))))
            .replace("__PORTRAITS_JSON__", js_json(load_portraits()))
            .replace("__SPEAKER_STYLES__", speaker_css)
            .replace("__PROJECT_TITLE__", html_text(data.get("project", "TACTICAL NARRATIVE")))
            .replace("__LEVEL_TITLE__", html_text(data.get("level", "GRAYBOX WALKTHROUGH"))))

    stem = os.path.splitext(os.path.basename(level_path))[0]
    out = os.path.join(output_dir(HERE), "walk.html" if stem in ("level", "vslice") else f"{stem}-walk.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out} ({len(html)} bytes) from {os.path.basename(level_path)}")
