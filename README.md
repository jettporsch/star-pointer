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
design, and enough math that the software side isn't just glue code.

## Architecture

This project splits into four jobs: find the star, know where the mount is
actually pointed, convert angles to steps, and generate the pulses.

Pulse generation has to be on the STM32 for microsecond timing and instant
limit switch response. The astronomy has to be on the laptop, because that's
where the catalog and the UI live.

Step conversion lives in Python for now. Two-star alignment needs the same 
math anyway, and prototyping it in Python was faster to debug. The firmware 
stays simple: it takes step moves, reports position, and handles the laser 
and stop. Porting the conversion to the STM32 is a possible later step.

That comes with a cost: more C, and firmware debugging is slower than Python.
I'm mitigating that by prototyping the alignment math in Python first, then
porting it to C with known-good numbers to check against.

The interface between the two sides is a small text command set over USB 
serial: move, status, stop, and laser.

```
  Laptop (Python)                    STM32                   Mechanics
  ---------------                    -----                   ---------
  star catalog          USB serial   command parser          NEMA 17 x2
  RA/Dec -> Alt/Az      -------->    mount transform  ---->  4:1 GT2 belt
  user interface        <--------    step generation         alt-az fork
                         status      homing + limits         laser + interlock
```

## Repo layout

| Path | Contents |
|---|---|
| `app/` | Python host application |
| `firmware/` | STM32 firmware |
| `hardware/` | KiCad project, BOM, CAD files |
| `docs/` | Design decisions, error budget, datasheets |

## Running the coordinate engine

Standard library only, no install step.

```bash
cd app
python3 skycoords.py        # current alt/az for every catalog star
python3 test_skycoords.py   # validation suite
```

## Validation

The transform is checked against physical facts rather than against another
library. If a check fails, its name points at the specific thing that broke.
Comparing to a reference implementation would only tell me the two disagree,
not where or which one is wrong.

13 checks, all passing.

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
   - [ ] Serial protocol spec (commands implemented, doc not written)
   - [x] Laser wiring and interlock
   - [x] Laser auto-off timer
   - [x] Two-star alignment
   - [x] End-to-end GOTO
   - [ ] Accuracy measurement across the sky
   - [ ] v2 mount: smaller frame, cable routing, electronics enclosure
   - [ ] Sidereal tracking
   - [ ] Custom PCB
