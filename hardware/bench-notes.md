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
