# Pointing error budget

**Target: ±0.5° total pointing error, anywhere above 20° altitude.**

## Why 0.5 degrees

This comes from what a person can see. The full moon is about 0.5° wide, so a
laser that lands within a moon's width of the intended star reads as a hit to
anyone standing there watching. Tighter than that doesn't buy a visible
improvement and would cost a lot of mechanical precision. Looser and it would
obviously be missing the star.

It's also achievable with the parts I bought, but not by much: 0.39° estimated
against the 0.5° target, leaving about 0.11° of headroom. Some of the terms in
that estimate are computed from the step size and gear ratio, but the
mechanical ones are engineering estimates until I measure them.

## How the errors combine

Independent errors don't add straight, they combine as root sum square. They're
independent, so they don't all push the same direction at the same moment.
Backlash might pull me left while flex pushes me right.

The consequence is the useful part. Take a 0.25° error and a 0.05° error.
Straight addition gives 0.30. RSS gives 0.255. The small one contributed almost
nothing.

So one large term dominates the total and shaving the small ones is wasted
effort. My biggest is alignment residual at 0.25°, and halving my smallest term
would move the total by about 0.001°. That's the rule the rest of this document
runs on: go after the biggest term, ignore anything under about 0.05°.

## Budget

| # | Source | Estimate | Measured | Notes |
|---|---|---|---|---|
| 1 | Microstep positional error | 0.07° | tbd | ±0.2 full step at motor, divided by 4 at the belt |
| 2 | Belt backlash and compliance | 0.15° | <0.01° | Wall test at 2.9 m, repeated moves with reversals |
| 3 | Frame and printed-part flex | 0.15° | tbd | Estimate, worst at high altitude |
| 4 | Two-star alignment residual | 0.25° | see below | Measured as part of the total, not separately |
| 5 | Laser collimation offset | 0.15° | ~0.9° | Fitted from the Oct 14 accuracy log, see below. Could also be altitude axis tilt |
| 6 | Homing repeatability | 0.05° | n/a | Switch homing dropped (decision D7); alignment absorbs the start position |
| 7 | Coordinate math residual | 0.02° | 0.01° | Measured by the test suite |
| 8 | Clock error | 0.01° | n/a | Sky moves 0.25°/min, so 1 s of clock error is 0.004° |
| 9 | Observer position error | <0.01° | n/a | 0.001° of latitude is about 100 m |
| | **RSS total** | **0.39°** | | |

## Measured result

Oct 14, 2026, v2 mount, aligned on Altair and Vega: **0.33° RMS, 0.44° worst**
over 8 stars between 52° and 78° altitude. Inside the target, with less
headroom than the estimate.

The misses have a pattern. Side-to-side error grows with altitude away from
the alignment stars: stars above them land right, stars below land left, and a
second alignment missed two stars 11° above the horizon by 1.1°. Random terms
like microstepping and flex can't do that. Two mount errors can, and the
two-star model includes neither:

- **Collimation (cone) error:** the laser not exactly square to the altitude
  axis. Best fit 0.88°.
- **Axis non-perpendicularity:** the altitude axis not exactly square to the
  azimuth axis. Best fit 0.64°.

Either one alone cuts the side-to-side RMS from 0.50° to 0.10 to 0.15°. With
11 stars the two can't be told apart, because both grow with altitude. Stars
near the horizon and near overhead separate them. Collimation was budgeted at
0.15°, so it was underestimated by about 6x, and it is now the dominant term.
Following the rule below, it gets fixed next: both terms go into the pointing
model, get fitted once from a calibration night, and get checked on a fresh
alignment.

The second alignment's 1.1° misses were at 11° altitude, below the 20° floor
this budget covers, and are left out of the headline number.

## Errors already eliminated

| Source | Would have cost | How it was removed |
|---|---|---|
| Neglecting precession | 0.15 to 0.37° | Applied IAU 1976 precession to epoch of date |
| Neglecting refraction | 0.02° at 45°, 0.5° at horizon | Applied Bennett's formula |
| Tripod not level | up to 1.0° per degree of tilt | Absorbed by two-star alignment |
| Magnetic declination | about 2° in North Texas | No magnetometer, heading comes from alignment |
| Direct-drive step size | 1.8° | 4:1 belt reduction |

## How each term gets measured

**Repeatability.** Command a slew away from a target and back, 20 times.
Measure how much the laser spot scatters on a wall at a known distance. Spot
displacement over distance gives the angle directly: 1 cm at 10 m is 0.057°.

**Backlash.** Approach the same target from clockwise, then from
counterclockwise. The difference between the two spot positions is the
backlash.

**Alignment residual.** Align on two stars, then command a third known star and
measure how far off it lands. Repeat across different parts of the sky. This is
the only one that needs a clear night.

## Rules

- Don't chase a term below 0.05°. At that level it contributes under 2% of the
  RSS total and the measurement itself is not that good.
- Update the Measured column as tests happen. An estimate that was never
  checked is not a budget, it is a guess.
- If the measured total exceeds 0.5°, either fix the dominant term or move the
  target and say so.
