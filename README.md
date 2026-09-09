# Star Pointer

A two-axis motorized mount that points a laser at any star you pick on your
laptop. It works out where to aim from your location, the current time, and a
two-star alignment done at setup.

**Status:** in development. Coordinate math is working. Motion control not
started.

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

I decided to put mount position and step conversion on the STM32 as well. If
the laptop kept its own copy, a missed step or a restarted app would make the
two disagree with nothing to catch it. This way the laptop never needs to know
about steps, gear ratios, or microstepping. All it does is name a direction.

That comes with a cost: more C, and firmware debugging is slower than Python.
I'm mitigating that by prototyping the alignment math in Python first, then
porting it to C with known-good numbers to check against.

The interface between the two sides is an alt/az pair over USB serial. That's
the whole contract.

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
- [ ] Serial protocol spec
- [ ] STM32 stepper control, both axes
- [ ] Limit switches and homing
- [ ] Mechanical build
- [ ] Two-star alignment
- [ ] End-to-end GOTO
- [ ] Custom PCB
- [ ] Laser interlock
- [ ] Sidereal tracking
