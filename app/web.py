from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request

from app.mount import Mount
from app.pointer import Pointer, WYLIE
from app.skycoords import CATALOG, look_up

app = Flask(__name__)
lock = Lock()  # one serial conversation at a time

try:
    pointer = Pointer(Mount())
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


@app.get("/api/where")
def where():
    if pointer is None:
        return jsonify(connected=False)
    with lock:
        alt, az = pointer.where()
        _, busy = pointer.m.status()
    return jsonify(connected=True, alt=alt, az=az, busy=any(busy))


@app.post("/api/stop")
def stop():
    if pointer is not None:
        with lock:
            pointer.m.stop()
    return jsonify(ok=True)


PAGE = """<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Star Pointer</title>
<style>
body { background:#000; color:#c33; font-family:-apple-system,sans-serif;
       margin:0 auto; padding:16px; max-width:520px; }
h1 { font-size:20px; margin:0 0 6px; }
#stat { color:#a44; min-height:1.3em; }
#msg { color:#e66; min-height:1.3em; margin-bottom:8px; }
button { background:#150000; color:#e44; border:1px solid #522; border-radius:8px;
         padding:12px; font-size:16px; width:100%; margin:4px 0;
         display:flex; justify-content:space-between; }
button:disabled { color:#522; border-color:#300; }
#stop { background:#400; justify-content:center; font-weight:bold; }
</style></head>
<body>
<h1>Star Pointer</h1>
<div id="stat">connecting...</div>
<div id="msg"></div>
<button id="stop" onclick="stopMount()">STOP</button>
<div id="list"></div>
<script>
const $ = id => document.getElementById(id);

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
  const r = await fetch('/api/point', { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }) });
  const j = await r.json();
  if (j.error) $('msg').textContent = j.error;
}

async function stopMount() {
  await fetch('/api/stop', { method: 'POST' });
  $('msg').textContent = 'stopped';
}

async function poll() {
  try {
    const j = await (await fetch('/api/where')).json();
    if (!j.connected) { $('stat').textContent = 'mount not connected'; return; }
    const az = ((j.az % 360) + 360) % 360;
    $('stat').textContent = `${j.busy ? 'moving' : 'at'} alt ${
      j.alt.toFixed(2)}° az ${az.toFixed(2)}°`;
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
