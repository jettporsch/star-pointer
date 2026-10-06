import time
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request

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
    out = []
    for name in CATALOG:
        t = look_up(name, WYLIE, now)
        out.append({"name": name, "alt": round(t.altitude_deg, 1),
                    "az": round(t.azimuth_deg, 1), "up": t.visible})
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
    return jsonify(ok=True)


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
                   laser=laser_wanted)


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

<h2>Stars</h2>
<div id="list"></div>
<script>
const $ = id => document.getElementById(id);
let stepDeg = 1, laserOn = false;

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
  } catch (e) { $('stat').textContent = 'server offline'; }
}

loadStars(); setInterval(loadStars, 30000);
poll(); setInterval(poll, 500);
</script>
</body></html>"""


if __name__ == "__main__":
    # 0.0.0.0 lets your phone connect on the same wifi.
    # Port 8000 because macOS uses 5000 for AirPlay.
    app.run(host="0.0.0.0", port=8000, threaded=True)
