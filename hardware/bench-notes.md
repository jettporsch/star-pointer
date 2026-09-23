# Bench Notes

## 2026-09-15: First stepper test

The motor is rated at 1.5A. Coil pairs are black/blue and green/red.

The driver is a DRV8825 with R100 sense resistors, so I = Vref × 2. I set Vref to 0.595V, which is about 1.19A, 80% of the rating.

SLEEP floated low on this board, so SLEEP and RESET are tied to 3V3 on the Nucleo.

STEP is on PB4 and DIR is on PB5.

I tested one revolution forward and back at 5ms per step, and it worked.

The only problem I hit was that SLEEP floated low, which kept Vref reading 0 until it was tied to 3V3.

## 2026-09-15: Second stepper test

The second driver's Vref is 0.603V, which is about 1.21A. Its 12V, 3V3, and ground all come from driver 1's rows.

Motor 2 pins: STEP2 is on PB10 (D6) and DIR2 is on PA8 (D7). I renamed the first motor's pins to STEP1 and DIR1.

I moved the step loop into a step_motor() function.

Driver 1's heatsink got hot after running motor 1 for around a minute, so I left motor 1 unplugged while setting driver 2.

I tested both motors one revolution forward and back, and it worked.

## 2026-09-15: Serial link test

Serial runs over USART2 through the ST-Link USB at 115200 baud. I read it with screen on the Mac.

First I tested sending hello every second. Then I used keys 1 to 4 to move each motor forward or backward one revolution. The Nucleo replies with what it did.

I added a uart_print() helper.

## 2026-09-15: Hardware timer step pulses

I switched step pulses from bit-banging to hardware timers. TIM3 CH1 on PB4 drives motor 1 and TIM2 CH3 on PB10 drives motor 2.

The timer clock is 84 MHz. Prescaler 83 gives 1 MHz, and period 4999 gives 5ms per step at 50% duty.

An interrupt at the end of each pulse counts down the steps and stops the timer at zero. Each motor is an Axis struct.

I tested both motors moving at once, and that worked. A second command mid-move replies with busy.

CubeMX overwrote the STEP1/STEP2 labels when I assigned the timer channels.

## 2026-09-16: Serial command protocol

The firmware now reads full lines over serial, with echo and backspace.

Commands:
- `M <axis> <steps>` moves axis 1 or 2 by a step count, negative for reverse
- `S` reports position and busy for both axes
- `X` stops both axes

Replies are `OK`, `ERR <reason>`, or data.

Position counts in the step interrupt, so it stays accurate after a stop.

I tested `M` and `S` on both motors and they worked as intended. `X` stopped motor 1 mid-move and `S` reported the partial position. Bad axis and unknown commands both return errors.

## 2026-09-16: Python serial interface

I added `app/mount.py`, a Python class that talks to the Nucleo over serial. It wraps the firmware commands as `move`, `status`, `stop`, and `wait`, and turns `ERR` replies into Python exceptions.

The first test failed because Python and the firmware got out of sync. The firmware's line buffer had leftover characters from an earlier screen session, so the first command came back as `ERR unknown`. I fixed it by sending a bare Enter on connect to clear the buffer, and by having `send` skip the echo and blank lines instead of expecting the echo first.

After the fix I tested moves on both axes, `wait`, stopping mid-move, and a bad axis error. All worked. The DRV8825 heatsinks ran hot during testing.

## 2026-09-16: 1/16 microstepping

Both DRV8825s are now wired for 1/16 microstepping. Before this, M0 to M2 were floating, which is full step.

Nucleo 3V3 moved to its own breadboard rail. That rail powers SLEEP on both drivers and M2 on each driver. M0 and M1 on each driver are tied to ground.

At 1/16, 3200 steps is exactly one motor revolution. With the 4:1 belt reduction that works out to about 35.6 steps per degree at the output.

I put a piece of tape on each motor shaft and confirmed 3200 steps gives one full revolution on both motors.

## 2026-09-21: Lazy susan stack test

Printed the lid center section, 2mm spacer, and test turntable on the P2S and assembled them with the real lazy susan.

I used M5 x 25 countersunk screws on both rings, since both rings have countersinks. Washers under the nuts for stability. All eight screws went in freely, so the 107 and 82 bolt circles are confirmed.

The turntable spins freely with no rubbing. The inner ring screw heads are reachable from below through the 96mm lid opening, as long as the outer ring screws go in first. That is the only assembly order that matters.

## 2026-09-21: 608 bearing housing test

Printed the bearing housing and retainer and assembled with a 608-2RS. The bearing pressed into the 22.0 pocket by hand and seated on the shoulder. Retainer held with four M3 x 25 socket head screws, washers on both sides.

The bearing spins freely with no extra drag after assembly. The printed shoulder only touches the outer ring, not the seal. This housing design goes into the fork.

## 2026-09-21: Degree-based pointing

Added `app/pointer.py`, which takes altitude and azimuth in degrees and moves both motors to match. It uses 35.56 steps per degree (200 steps x 16 microsteps x 4:1 belt / 360). Targets are calculated from home every time so rounding error does not build up.

Azimuth stays between -180 and +180 from home and never crosses that point, so the cable loop cannot wind past its limit. Altitude is limited to 0 to 90. For now, wherever the motors are at connect counts as home. Endstop homing replaces that later.

Tested with tape flags on both motor shafts. 90 degrees at the output is exactly one motor rev, which matched on both axes. Going from az 90 to az 180 went backwards to -180 as intended. Altitude 95 was refused.

## 2026-09-21: Pointing at stars by name

Hooked `pointer.py` up to `skycoords.py`. `point_at("Vega")` now looks up the star, converts it to altitude and azimuth for Wylie at the current time, and moves both motors there. Stars below the horizon are refused.

For now, home has to be level and facing true north for the pointing to be right. Endstop homing and calibration handle that once the mount is built.

Tested with Vega, Arcturus, and Sirius. Vega's commanded and actual positions agreed within 0.012 degrees, which is under half a step, so the only error is rounding to whole steps. Sirius was below the horizon and was refused with no movement.

## 2026-09-21: Step speed

Added a `V <us>` serial command that sets the step period for both axes in microseconds, so speed can be tested live without rebuilding. Refuses changes while a motor is moving.

Tested one full rev at each speed with a tape flag, unloaded, no acceleration ramp:
- Motor 1: clean all the way down to 100us (10,000 steps/s)
- Motor 2: stalls at 100, hit or miss at 150, clean at 200 and up

A stalled motor makes noise but doesn't turn, and the firmware still counts the steps, so position is silently wrong. That's why the default has margin.

Default step period is now 600us at startup, 3x slower than motor 2's clean limit. That's about 47 degrees per second at the output, 180 degrees in about 4 seconds, down from 30 seconds before. To revisit once the mount is under real load, and after checking driver 2's Vref, which may explain the difference between motors.

## 2026-09-21: Web interface

Added `app/web.py`, a Flask app that runs on the laptop at localhost:8000. It lists all 22 catalog stars sorted by altitude with live alt/az, grays out stars below the horizon, points the mount when a star is tapped, shows live position, and has a stop button.

Moves start without blocking, and the page polls position twice a second, so stop works mid-move. A lock keeps requests from talking over each other on the serial port.

Tested in the browser: tapping Vega moved the motors there and the readout showed when it arrived. Stop halted a move immediately. Below-horizon stars can't be tapped. Speed at the 600us default feels right for pointing.

Correction to the step speed note: both drivers are set to nearly the same Vref (0.595V and 0.603V), so current doesn't explain motor 2's lower speed limit. Likely normal variation between motors.

Current UI is dark red for night vision. The plan later is a purple and yellow theme to match the mount's final look, with red kept as a night mode.

## 2026-09-22: Fork stage assembled

Printed and assembled the gusseted fork: two uprights with 608 bearings and retainers, slotted altitude motor plate with a spare NEMA 17, and the 196mm stage turntable, mounted on the lazy susan and lid center test.

The shaft passes through both bearings and turns freely with the feet tightened. Shaft collars on each side stop it sliding. Both pulleys reach their specified positions and their tooth bands line up. No visible flex at the top of the uprights under hand pressure. Belt tension is reasonable with the motor near mid-slot.

Ordered the 280mm GT2 belt, which is the calculated length for the 88mm center distance the slots are built around.

Next is the laser cradle.

## 2026-09-22: Laser control

Added `L 1` and `L 0` serial commands to switch the laser on and off through PA9 (D8 on the header). The pin starts low at power-up, so the laser is off until it's deliberately turned on. `axis_stop_all` also drives it low, so the stop command kills the beam along with the motors.

Tested with a multimeter on D8: 3.3V after `L 1`, 0V after `L 0`, and 0V after `X`.

The laser itself needs more current than a GPIO pin can supply, so it switches through an NPN transistor with a 1k resistor on the base, laser red to 5V and black to the collector. Transistor and resistor kits are ordered. The firmware side is done and waiting on parts.

## 2026-09-22: Laser cradle

Printed and fitted the laser cradle. It clamps the 8mm rod with the lower cap and holds the laser module with the upper cap. Both use the bore sizes from the coupon tests, 8.2 for the rod and 12.0 for the laser.

Rotated the rod a full 360 degrees with the laser mounted and nothing contacts the uprights, belt, or pulley. Altitude only needs 0 to 90, so there's plenty of room.

The specified screws are longer than needed and stick out past the nuts. Cosmetic, swapping for shorter ones.

## 2026-09-22: Altitude home assembly

Installed the altitude home hardware on the left upright: a bracket that bolts over the existing bearing retainer using the same four screws, an adjustable switch carrier, and a cam that clamps to the rod outside the fork.

It works as intended. The cam reaches the lever and the carrier slides to set the trip height.

The carrier is still adjustable because I don't know this switch's actual sensitivity yet. Next step is measuring the real trip point, release point, and how much lever travel is left before it bottoms out, using a multimeter across the switch contacts. Those numbers set the cam lift and let the carrier height be fixed in the next revision instead of adjustable.
