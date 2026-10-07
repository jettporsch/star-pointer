# Star Pointer

A two-axis motorized mount that points a laser at any star you pick on your
laptop. It works out where to aim from your location, the current time, and a
two-star alignment done at setup.

**Status:** working prototype. After a two-star alignment it points the laser 
at a selected star, controlled from a phone or laptop. Next up is measuring 
accuracy across the sky and a cleaner v2 mount.

**Design target:** ±0.5° pointing accuracy.

## Why I built this

I've always been fascinated with space and astronomy, and I wanted a personal
project that used something I'm passionate about while digging into hardware.
This one covers embedded firmware, motion control, PCB design, mechanical
design, and enough math that the software side isn't just just connecting 
libraries together.

## Architecture

This project splits into four jobs: find the star, know where the mount is
actually pointed, convert angles to steps, and generate the pulses.

Pulse generation has to be on the STM32 for microsecond timing and an
instant stop. The astronomy has to be on the laptop, because that's
where the catalog and the UI live.

Step conversion lives in Python for now. Two-star alignment needs the same 
math anyway, and prototyping it in Python was faster to debug. The firmware 
stays simple: it takes step moves, reports position, and handles the laser 
and stop. Porting the conversion to the STM32 is a possible later step.

The interface between the two sides is a small text command set over USB 
serial: move, status, stop, and laser.

```
  Laptop (Python)                    STM32                   Mechanics
  ---------------                    -----                   ---------
  star catalog          USB serial   command parser          NEMA 17 x2
  RA/Dec -> Alt/Az      -------->    step generation  ---->  4:1 GT2 belt
  two-star alignment    <--------    position count          alt-az fork
  angles -> steps        status      laser + auto-off        laser
  web UI (phone/laptop)              stop
```

## Repo layout

| Path | Contents |
|---|---|
| `app/` | Python host application |
| `firmware/` | STM32 firmware |
| `hardware/` | BOM, dimensions, CAD files, bench notes |
| `docs/` | Design decisions, error budget, serial protocol |

## Running the coordinate engine

Standard library only, no install step.

```bash
cd app
python3 skycoords.py        # current alt/az for every catalog star
python3 test_skycoords.py   # validation suite
```

## Running the mount

Needs Flask and pyserial: `pip3 install flask pyserial`.

```bash
python3 -m app.align   # desk test: simulated tilted mount, no hardware needed
python3 -m app.web     # web UI on http://localhost:8000
```

The web app listens on the local network, so a phone on the same wifi can open
it at the laptop's IP address on port 8000.

## Using it outside

1. Stage facing roughly south. That puts the cable limit (half a turn either
   way) due north, where few stars cross. The laser can rest at any angle.
2. 12V on first, so the motors lock the mount in place, then start the web app.
3. Jog the beam onto a bright star, sighting straight down the beam from behind
   the laser, pick it in the Align list, and tap "Beam is on this star."
4. The Align list now ranks every other star as a partner for the first one.
   Pick one rated "good" and do the same.
5. Tap any star in the list to point at it.

Choosing the second star matters more than it looks. With the same 0.1°
centering slip, a good pair keeps every GOTO within about 0.1°, while a poor
one can throw some off by several degrees. The app simulates each pair and
rates it, so there's nothing to memorize.

**Measuring accuracy:** after a GOTO, jog the beam onto the star and tap
"Centered." The app logs how far the GOTO landed from the star, and in which
direction, to `data/accuracy.csv`, and shows the RMS and worst miss for the
current alignment. Alignment stars are logged but left out of the stats.

Never point it at aircraft. The laser turns itself off 60 seconds after the
last command if the app goes away.

## Results so far

- **Step scale and backlash (wall test at 2.9 m):** 100 steps moved the beam
  2.8° on both axes, matching the gear math. Repeated moves with direction
  reversals landed back within about half a millimeter, under 0.01°.
- **First on-sky GOTO (Oct 6, 2026):** aligned on Altair and Vega from a
  driveway sloped about 4°. Alignment reported the base 3° off level and the
  laser's starting angle within 0.1°, both matching the real setup. GOTO to
  Deneb and Polaris landed on the star with no manual correction.
- **Not yet measured:** pointing error in degrees across the sky.

Details in `hardware/bench-notes.md`.

## Validation

The transform is checked against physical facts rather than against another
library. If a check fails, its name points at the specific thing that broke.
Comparing to a reference implementation would only tell me the two disagree,
not where or which one is wrong.

14 checks, all passing.

## References

Sidereal time, Julian date, and precession formulas follow Meeus,
*Astronomical Algorithms*. Refraction uses Bennett's formula.

## Progress

- [x] RA/Dec to alt/az transform, precession, refraction
- [x] Validation suite
- [x] STM32 stepper control, both axes
- [x] Altitude homing
- [x] Prototype mount built
- [x] Azimuth zero (manual index mark; switch homing kept as a test tool)
- [x] Serial protocol spec
- [x] Laser wiring and interlock
- [x] Laser auto-off timer
- [x] Two-star alignment
- [x] End-to-end GOTO
- [ ] Accuracy measurement across the sky
- [ ] v2 mount: smaller frame, cable routing, electronics enclosure
- [ ] Sidereal tracking
- [ ] Custom PCB
