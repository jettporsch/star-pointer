import csv
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request

from app.align import pair_sensitivity
from app.mount import Mount
from app.pointer import (Pointer, WYLIE, STEPS_PER_DEG,
                         ALT_AXIS, AZ_AXIS, ALT_SIGN, AZ_SIGN)
from app.skycoords import CATALOG, look_up

app = Flask(__name__)
lock = Lock()  # one serial conversation at a time

# Laser state as the page sees it. While the page is open and the laser is
# switched on, polling re-sends L 1 every few seconds. If the page or laptop
# goes away, the firmware's 60 s auto-off kills the beam.
laser_wanted = False
last_arm = 0.0
REARM_S = 10

# Accuracy test: after a GOTO, jog the beam onto the star and tap Centered.
# Every result is appended to data/accuracy.csv. The on-page summary only
# covers the current alignment, since a new alignment changes the model.
last_goto = None
results = []
ACCURACY_CSV = Path(__file__).resolve().parent.parent / "data" / "accuracy.csv"
CSV_FIELDS = ["time_utc", "star", "star_alt_deg", "star_az_deg", "miss_up_deg",
              "miss_right_deg", "miss_total_deg", "aligned_on", "is_align_star"]


def summary():
    test = [r for r in results if not r["is_align_star"]]
    if not test:
        return None
    totals = [r["total"] for r in test]
    return {"n": len(test), "rms": math.sqrt(sum(x * x for x in totals) / len(totals)),
            "max": max(totals)}

try:
    pointer = Pointer(Mount())
    pointer.m.send("V 2000")  # 600us default stalls az with the full stage on it
except Exception as e:
    pointer = None
    print(f"mount not connected: {e}")


@app.get("/")
def index():
    return PAGE


@app.get("/api/stars")
def stars():
    now = datetime.now(timezone.utc)
    # With one alignment star recorded, rate every other star as a partner.
    first = None
    if pointer is not None and len(pointer.align.stars) == 1:
        name1 = pointer.align.stars[0][0]
        t1 = look_up(name1, WYLIE, now)
        first = (t1.altitude_deg, t1.azimuth_deg)
    out = []
    for name in CATALOG:
        t = look_up(name, WYLIE, now)
        s = {"name": name, "alt": round(t.altitude_deg, 1),
             "az": round(t.azimuth_deg, 1), "up": t.visible, "pair": None}
        if first is not None and t.visible and name != name1:
            s["pair"] = pair_sensitivity(first, (t.altitude_deg, t.azimuth_deg))
        out.append(s)
    out.sort(key=lambda s: -s["alt"])
    return jsonify(out)


@app.post("/api/point")
def point():
    if pointer is None:
        return jsonify(error="mount not connected"), 503
    name = request.json["name"]
    t = look_up(name, WYLIE, datetime.now(timezone.utc))
    if not t.visible:
        return jsonify(error=f"{name} is below the horizon"), 400
    try:
        with lock:
            pointer.goto(t.altitude_deg, t.azimuth_deg, wait=False)
    except RuntimeError:
        return jsonify(error="still moving, wait or hit stop"), 409
    global last_goto
    last_goto = name
    return jsonify(ok=True)


@app.post("/api/centered")
def centered():
    if pointer is None:
        return jsonify(error="mount not connected"), 503
    if last_goto is None:
        return jsonify(error="tap a star in the list first, then jog onto it"), 400
    if len(pointer.align.stars) < 2:
        return jsonify(error="align on two stars first"), 400
    with lock:
        if any(pointer.m.status()[1]):
            return jsonify(error="wait for the mount to stop first"), 409
        r = pointer.miss(last_goto)
    align_names = [s[0] for s in pointer.align.stars]
    r["is_align_star"] = last_goto in align_names
    results.append(r)

    new_file = not ACCURACY_CSV.exists()
    ACCURACY_CSV.parent.mkdir(exist_ok=True)
    with ACCURACY_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(CSV_FIELDS)
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    r["star"], f"{r['alt']:.3f}", f"{r['az']:.3f}",
                    f"{r['up']:.3f}", f"{r['right']:.3f}", f"{r['total']:.3f}",
                    " + ".join(align_names), int(r["is_align_star"])])
    return jsonify(ok=True, result=r, summary=summary())


@app.post("/api/jog")
def jog():
    if pointer is None:
        return jsonify(error="mount not connected"), 503
    axis = request.json.get("axis")
    deg = float(request.json.get("deg", 0))
    if axis not in ("alt", "az") or not 0 < abs(deg) <= 30:
        return jsonify(error="bad jog"), 400
    motor, sign = (ALT_AXIS, ALT_SIGN) if axis == "alt" else (AZ_AXIS, AZ_SIGN)
    steps = round(deg * STEPS_PER_DEG) * sign
    try:
        with lock:
            pointer.m.move(motor, steps)
    except RuntimeError:
        return jsonify(error="still moving, wait or hit stop"), 409
    return jsonify(ok=True)


@app.post("/api/align")
def align():
    if pointer is None:
        return jsonify(error="mount not connected"), 503
    name = request.json.get("name", "")
    try:
        with lock:
            if any(pointer.m.status()[1]):
                return jsonify(error="wait for the mount to stop first"), 409
            report = pointer.record_star(name)
            results.clear()
    except (ValueError, KeyError) as e:
        return jsonify(error=str(e).strip("'\""), report=pointer.align.report), 400
    return jsonify(ok=True, report=report)


@app.post("/api/align/reset")
def align_reset():
    if pointer is not None:
        pointer.align.reset()
    results.clear()
    return jsonify(ok=True)


@app.post("/api/laser")
def laser():
    global laser_wanted, last_arm
    if pointer is None:
        return jsonify(error="mount not connected"), 503
    on = bool(request.json.get("on"))
    with lock:
        pointer.m.send("L 1" if on else "L 0")
    laser_wanted = on
    last_arm = time.time()
    return jsonify(ok=True, laser=on)


@app.get("/api/where")
def where():
    global last_arm
    if pointer is None:
        return jsonify(connected=False)
    with lock:
        if laser_wanted and time.time() - last_arm > REARM_S:
            pointer.m.send("L 1")
            last_arm = time.time()
        alt, az = pointer.where()
        _, busy = pointer.m.status()
    return jsonify(connected=True, alt=alt, az=az, busy=any(busy),
                   laser=laser_wanted, align=pointer.align.report,
                   nstars=len(pointer.align.stars), last_goto=last_goto,
                   results=results[-8:], summary=summary())


@app.post("/api/stop")
def stop():
    global laser_wanted
    if pointer is not None:
        with lock:
            pointer.m.stop()  # X also kills the laser in firmware
    laser_wanted = False
    return jsonify(ok=True)


PAGE = """<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Star Pointer</title>
<style>
body { background:#000; color:#c33; font-family:-apple-system,sans-serif;
       margin:0 auto; padding:16px; max-width:520px; }
h1 { font-size:20px; margin:0 0 6px; }
h2 { font-size:15px; margin:18px 0 6px; color:#a44; }
#stat { color:#a44; min-height:1.3em; }
#msg { color:#e66; min-height:1.3em; margin-bottom:8px; }
button { background:#150000; color:#e44; border:1px solid #522; border-radius:8px;
         padding:12px; font-size:16px; width:100%; margin:4px 0;
         display:flex; justify-content:space-between; }
button:disabled { color:#522; border-color:#300; }
#stop { background:#400; justify-content:center; font-weight:bold; }
.pad { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }
.pad button, .row button { justify-content:center; margin:0; padding:16px 0;
                           font-size:22px; touch-action:manipulation; }
.row { display:flex; gap:8px; margin-top:8px; }
.row button { font-size:15px; padding:12px 0; }
.row button.on { background:#400; color:#f66; border-color:#a33; }
select { background:#150000; color:#e44; border:1px solid #522; border-radius:8px;
         padding:12px; font-size:16px; width:100%; margin:4px 0; }
#alignstat, #accstat { color:#a44; min-height:1.3em; font-size:14px; }
#acclist { font-size:14px; color:#a44; }
#acclist div { display:flex; justify-content:space-between; padding:2px 0; }
</style></head>
<body>
<h1>Star Pointer</h1>
<div id="stat">connecting...</div>
<div id="msg"></div>
<button id="stop" onclick="stopMount()">STOP</button>

<h2>Jog</h2>
<div class="pad">
  <span></span><button onclick="jog('alt', 1)">&#9650;</button><span></span>
  <button onclick="jog('az', -1)">&#9664;</button>
  <span></span>
  <button onclick="jog('az', 1)">&#9654;</button>
  <span></span><button onclick="jog('alt', -1)">&#9660;</button><span></span>
</div>
<div class="row" id="sizes">
  <button data-deg="5">5&deg;</button>
  <button data-deg="1" class="on">1&deg;</button>
  <button data-deg="0.1">0.1&deg;</button>
  <button data-deg="0.03">fine</button>
</div>
<div class="row"><button id="laser" onclick="toggleLaser()">laser off</button></div>

<h2>Align</h2>
<div id="alignstat">not aligned</div>
<select id="alignstar"></select>
<button onclick="recordStar()" style="justify-content:center">Beam is on this star</button>
<button onclick="resetAlign()" style="justify-content:center">Reset alignment</button>

<h2>Accuracy</h2>
<div id="accstat">align, tap a star below, jog onto it, then tap Centered</div>
<button id="centered" onclick="markCentered()" style="justify-content:center">Centered</button>
<div id="acclist"></div>

<h2>Stars</h2>
<div id="list"></div>
<script>
const $ = id => document.getElementById(id);
let stepDeg = 1, laserOn = false, alignRated = false;

for (const b of $('sizes').children) {
  b.onclick = () => {
    stepDeg = parseFloat(b.dataset.deg);
    for (const o of $('sizes').children) o.classList.toggle('on', o === b);
  };
}

async function post(url, body) {
  const r = await fetch(url, { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}) });
  return r.json();
}

async function jog(axis, dir) {
  const j = await post('/api/jog', { axis, deg: dir * stepDeg });
  $('msg').textContent = j.error || '';
}

function showLaser() {
  $('laser').textContent = laserOn ? 'laser ON' : 'laser off';
  $('laser').classList.toggle('on', laserOn);
}

async function toggleLaser() {
  const j = await post('/api/laser', { on: !laserOn });
  if (j.error) { $('msg').textContent = j.error; return; }
  laserOn = j.laser; showLaser();
}

async function loadStars() {
  const stars = await (await fetch('/api/stars')).json();
  // After the first alignment star, list partners best first. The number is
  // how far a 0.1 deg centering slip on that star would throw off other GOTOs.
  const rated = stars.some(s => s.pair !== null && s.pair !== undefined);
  const label = s => s.pair === null ? (rated ? ' - too close' : '')
    : ` - ${s.pair <= 0.15 ? 'good' : s.pair <= 0.4 ? 'ok' : 'poor'} pair`;
  let opts = stars.filter(s => s.up);
  if (rated) opts = opts.slice().sort((a, b) =>
    (a.pair ?? 1e9) - (b.pair ?? 1e9));
  const keep = rated && !alignRated ? null : $('alignstar').value;
  $('alignstar').innerHTML = opts.map(s =>
    `<option value="${s.name}">${s.name} (alt ${s.alt}&deg; az ${s.az}&deg;)${label(s)}</option>`
  ).join('');
  if (keep) $('alignstar').value = keep;
  alignRated = rated;
  $('list').innerHTML = '';
  for (const s of stars) {
    const b = document.createElement('button');
    b.disabled = !s.up;
    b.innerHTML = `<span>${s.name}</span><span>${
      s.up ? `alt ${s.alt}&deg; az ${s.az}&deg;` : 'below horizon'}</span>`;
    b.onclick = () => pointAt(s.name);
    $('list').appendChild(b);
  }
}

async function pointAt(name) {
  $('msg').textContent = `pointing at ${name}`;
  const j = await post('/api/point', { name });
  if (j.error) $('msg').textContent = j.error;
}

async function recordStar() {
  const name = $('alignstar').value;
  const j = await post('/api/align', { name });
  $('msg').textContent = j.error || `recorded ${name}`;
  loadStars();
}

async function resetAlign() {
  await post('/api/align/reset');
  $('msg').textContent = 'alignment cleared';
  loadStars();
}

async function markCentered() {
  const j = await post('/api/centered');
  if (j.error) { $('msg').textContent = j.error; return; }
  const r = j.result;
  $('msg').textContent = `${r.star}: missed by ${r.total.toFixed(2)}°`;
}

function showAccuracy(j) {
  $('centered').textContent = j.last_goto ? `Centered on ${j.last_goto}` : 'Centered';
  const s = j.summary;
  $('accstat').textContent = s
    ? `${s.n} star${s.n > 1 ? 's' : ''}: RMS ${s.rms.toFixed(2)}°, worst ${s.max.toFixed(2)}° (target 0.5°)`
    : 'align, tap a star below, jog onto it, then tap Centered';
  $('acclist').innerHTML = (j.results || []).slice().reverse().map(r =>
    `<div><span>${r.star}${r.is_align_star ? ' (align star)' : ''}</span><span>${
      r.total.toFixed(2)}°  (${r.up >= 0 ? 'high' : 'low'} ${Math.abs(r.up).toFixed(2)}, ${
      r.right >= 0 ? 'right' : 'left'} ${Math.abs(r.right).toFixed(2)})</span></div>`).join('');
}

async function stopMount() {
  await post('/api/stop');
  laserOn = false; showLaser();
  $('msg').textContent = 'stopped';
}

async function poll() {
  try {
    const j = await (await fetch('/api/where')).json();
    if (!j.connected) { $('stat').textContent = 'mount not connected'; return; }
    const az = ((j.az % 360) + 360) % 360;
    $('stat').textContent = `${j.busy ? 'moving' : 'at'} alt ${
      j.alt.toFixed(2)}° az ${az.toFixed(2)}°`;
    if (j.laser !== laserOn) { laserOn = j.laser; showLaser(); }
    $('alignstat').textContent = j.align;
    showAccuracy(j);
  } catch (e) { $('stat').textContent = 'server offline'; }
}

loadStars(); setInterval(loadStars, 30000);
poll(); setInterval(poll, 500);
</script>
</body></html>"""


if __name__ == "__main__":
    # 0.0.0.0 lets your phone connect on the same wifi.
    # Port 8000 because macOS uses 5000 for AirPlay.
    try:
        app.run(host="0.0.0.0", port=8000, threaded=True)
    finally:
        # Ctrl-C: kill the beam right away instead of waiting for auto-off
        if pointer is not None:
            try:
                pointer.m.send("L 0")
            except Exception:
                pass
