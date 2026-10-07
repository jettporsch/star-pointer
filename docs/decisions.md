# Design decisions

One entry per real decision: what I chose, what I rejected, and why. Written
when the decision is made, not reconstructed afterward.

The point is to be able to answer "why did you do it that way" months later
without guessing at my own reasoning.

## D1. Alt-az mount, not equatorial

**Chose:** two-axis altitude/azimuth mount.

**Rejected:** equatorial mount.

**Why:** an equatorial mount's advantage is smooth single-axis tracking, which
matters for long-exposure astrophotography. I'm pointing a laser, so that buys
me nothing. In exchange I'd be taking on a tilted frame that makes the
coordinate math messier, plus a counterweight and a mount angled to my
latitude. Re-pointing every 10 seconds works fine on two axes.

## D2. STM32, not Arduino

**Chose:** STM32 (Nucleo-F401RE).

**Rejected:** Arduino.

**Why:** Arduino has a shallower learning curve, but it abstracts away the
hardware I want to work at. I already have STM32 experience from a previous
project, so my time goes into motion control instead of learning a new
toolchain. The STM32's hardware timers generate step pulses without CPU
involvement, which is what makes precise stepping possible. It also keeps the
project at the register and peripheral level.

## D3. Belt reduction, 4:1

**Chose:** GT2 belt, 20-tooth motor pulley to 80-tooth output pulley, on both
axes.

**Rejected:** direct drive; 3D printed spur gears; 5:1 with a 100-tooth pulley.

**Why:** direct drive makes 1.8° the finest possible move, and my pointing
budget is ±0.5°, which takes it off the table immediately. Microstepping
doesn't fix this. The rotor still settles toward the nearest full step under
load, so it buys smoothness, not accuracy.

Gearing down solves it mechanically. At 4:1, one full step at the motor becomes
0.45° at the output, and the reduction divides load-induced error by four as
well.

I went with belts rather than 3D printed gears because layer lines on a printed
tooth face give a degree or more of backlash. A tensioned GT2 belt is nearly
backlash-free.

I originally specced 5:1, but 100-tooth pulleys are rare and expensive in
aluminum, and printing one would put me back in backlash territory. 80-tooth is
common and cheap, and 80 against my 20-tooth motor pulley is 4:1.

## D4. Two-star alignment, not a magnetometer

**Chose:** manual two-star alignment.

**Rejected:** magnetometer for heading.

**Why:** a magnetometer is cheap, but it reads magnetic north, and true north
is about 2° off from that in North Texas. That correction is easy. The real
problem is that it would sit inches from two stepper motors and a steel frame,
so my own hardware corrupts the reading and no correction fixes that.

With two-star alignment I manually slew to two stars I can identify, confirm
each one, and the app records the motor positions. From those two
observations it solves for how the mount is actually oriented. One procedure
handles heading and leveling at once, so a tripod that's 1° out of level gets
absorbed instead of costing me up to 1° of pointing error.

The cost is that it's a manual step at every setup, and I have to be able to
identify two stars.

## D5. DRV8825 stepper drivers

**Chose:** DRV8825.

**Rejected:** A4988, TMC2209.

**Why:** the DRV8825 is pin-compatible with the A4988 but handles more current
with finer microstepping, at the same price. The TMC2209 is nicer on paper,
mainly for sensorless homing, but that is unreliable on a low-torque belt axis,
and homing turned out to be unnecessary anyway (see D7).

## D6. Mount position and step conversion live on the STM32

**Chose:** the laptop sends an alt/az pair. The STM32 applies the alignment,
converts to steps, and tracks its own position.

**Rejected:** the laptop computing step counts and sending those instead.

**Why:** if the laptop kept its own copy of mount position, a missed step or a
restarted app would make the two disagree with nothing to catch it. Keeping one
authority, on the thing bolted to the motors, removes that class of bug. The
laptop never needs to know about steps, gear ratios, or microstepping. All it
does is name a direction, which also means anything that can send an alt/az
pair could drive the mount.

The cost is more C, and firmware debugging is slower than Python. I'm
mitigating that by prototyping the alignment math in Python first, then porting
it to C with known-good numbers to check against.

**Revised, Oct 2026:** step conversion and alignment ended up in Python, and
the firmware only takes step moves. Once alignment was written in Python, it
already had to do the angle math, and splitting it across two languages bought
nothing. The missed-step concern above is real but didn't show up: the wall
test came back within 0.01° after repeated moves, and the one real failure on
the sky (a slipping pulley) was mechanical, so neither side's count would have
caught it. Porting to C is still an option, not a requirement.

## D7. No limit switch homing

**Chose:** start with the stage on a pencil mark and the laser roughly flat,
then let two-star alignment work out the rest.

**Rejected:** endstop homing on both axes.

**Why:** two-star alignment solves for where az zero points, how far off level
the base is, and how far off flat the laser started, every session. Homing only
told the mount where it was relative to its own base, which alignment throws
away anyway. The only real job left was keeping the cables from winding past
their slack, and an index mark does that.

I built and tested switch homing first. Altitude worked. Azimuth took days of
cam reprints and still scattered about ±0.4°, and most of the 6° hysteresis I
measured turned out to be the switch itself, not the drive. That effort was the
signal to step back and ask what homing was actually for.

**Cost:** two rules at startup (stage on the mark, laser roughly flat, 12V on
before the app). A slot that locks the turntable with a coin is on the v2 list
to make the az mark more precise.

## Template

```
## Dn. Title

**Chose:**
**Rejected:**
**Why:**
```
