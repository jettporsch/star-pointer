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

## 2026-09-23: Altitude drive powered test

Fitted the 280mm GT2 belt between the 20T motor pulley and the 80T shaft pulley and ran the altitude axis under power for the first time.

Started slow at 2000us with small moves, then worked up. 3200 steps gives 90 degrees of tilt, which matches the 35.56 steps per degree from the 4:1 reduction. Moving out 3200 and back 3200 returned the laser to a tape mark, so no teeth were skipped. Motion is smooth, the belt tracks without rubbing, and nothing catches through the range.

## 2026-09-23: Altitude endstop reading

Added an `E` command that reports endstop state over serial. The altitude switch is on PA10 (D2) with an internal pull-up.

The endstop boards have their own 10K pull-up, LED, and debounce cap, wired out to S, G, V. Wired G to ground, S to D2, and V to 3V3. With that board, the pin reads high when the lever is free and low when pressed, so the firmware inverts it. `E` now reports 0 for free and 1 for triggered.

Tradeoff worth noting: going through the board's S pin means a disconnected wire reads as not triggered, so homing would keep driving. Wiring S straight to the switch's NC pin instead would fail toward stopping, at the cost of the board's LED and debounce. Keeping the current wiring while homing is supervised on the bench.

Next step is using `E` to find the exact step count where the cam trips, which sets level zero without measuring by hand.

## 2026-09-23: Altitude homing

Installed the V2 fixed home bracket, carrier, and cam. Homing approaches level from below, because coming down the lever tip catches the cam's clamp slot. The cam is clamped so the switch trips exactly at level, set with a level while the motor held position.

Added an `H` command. It backs off below the cam if already on it, drives up until the switch trips, backs off 400 steps, then creeps up at 6000us in 5-step increments and calls the first trip zero. Worst case overshoot is 5 steps, 0.14 degrees. Each search is bounded, so a disconnected switch errors out instead of driving on.

Tested repeatedly from different starting positions below level and it lands level each time.

Also found the 600us default step speed is too fast now that the cradle, laser, and belt are on the axis. It stalls starting from rest. 2000us works. Acceleration ramps would let it run faster and start reliably, worth doing later.

Shaft collars installed inside the fork, one against each bearing, with no added drag.

Note on procedure: the cam is the harder thing to set and the cradle is the easier one, so it would be better to treat the cam as the fixed reference and level the cradle against it, rather than the reverse. If anything slips, home first, then loosen the cradle and level the laser to the cam's edge.

## 2026-10-04: Azimuth endstop debugging

The azimuth endstop read 0 no matter what. Two separate faults stacked on top of each other.

First, both endstops went dead at once. The 3V3 wire feeding the endstop boards had worked partly out of the breadboard. Reseating it brought altitude back.

Second, the azimuth pin was wrong in firmware. PB2 was listed as D10, but D10 on the Nucleo-F401RE is PB6. PB2 is only on the Morpho header, so the firmware was reading a pin with nothing attached, and the internal pullup held it high forever. Moved the config to PB6 in CubeMX, changed AZ_ES_PIN to GPIO_PIN_6, and left the wire on D10. E now reports AZ correctly from the lever.

Third, mechanical. With the electrical path working, the cam lobe turned out to be about 1mm short of pushing the lever to its trip point. Contact happens but never clicks. Reprinting the cam with 1mm more lift at the lobe peak. The lever has about 1mm of overtravel past the trip, so 1mm more lift should trip without bottoming it.

Next after the reprint: confirm the trip in both rotation directions, measure how many degrees the lobe stays triggered, then write the azimuth homing routine. Unlike altitude's wide plateau, this cam has a single bump so the switch is off for most of a revolution.

## 2026-10-04: Azimuth cam reprint and homing

The reprinted cam with 1mm more lift trips the switch, and the lever doesn't bottom out on the lobe peak.

The az belt had too much sag with the motor on the adjustable slides. Next revision of the az motor mount should be a fixed position, slightly farther back, instead of slotted.

STEP2 dropped out twice. M 2 replied OK and S counted the steps, but the motor was silent and didn't turn. The connection between D6 and driver 2's STEP pin was intermittent. Reseating fixed it once, then it came back, so I replaced the jumper and pressed driver 2 down into the breadboard. Breadboard contacts keep causing problems, the drivers should go on a soldered board eventually.

Positive az steps turn the stage clockwise looking down.

Added `app/az_cam_sweep.py`. It steps az 5 steps at a time, checks E after each, and logs every switch edge forward then back. Currently set to a 120 degree sweep.

Results: the lobe is about 80 degrees wide (on from 2649 to 5489 going CW, 5264 to 2434 going CCW). There's about a 6 degree gap between directions on both edges (215 and 225 steps). That could be switch hysteresis or belt backlash, this test can't separate them. The CW trip edge was clean. The release edge was less consistent and chattered once.

The cables went tight near the end of the 120 degree sweep. Moved things closer for more slack. Az needs a full 360 degrees of cable travel with home in the middle.

An 80 degree lobe only partly fixes the power-up direction problem. Switch on means you know where you are, switch off covers the other 280 degrees and is still ambiguous. Next cam revision is a half-moon: same lift, same ramp on the CW-trip edge, raised section stretched to 180 degrees. Then the switch state at power-up tells homing which way to go.

Added an `H AZ` command. If on the lobe, it drives CCW until it releases and backs off 400 more. Then it searches CW until it trips, backs off 400, and creeps CW one step at a time to the trip edge, which is zero. `HOMED` prints where the old count thought the edge was before zeroing, so repeatability shows up directly. `H` still homes altitude.

Fixed a bug where `move_wait` skipped moves if the axis was still busy from a previous command.

Repeatability is about plus or minus 13 steps, roughly 0.38 degrees, over 6 homes from both sides. The error budget has 0.05 degrees for homing. Either the switch trip point is that loose because the cam ramp is shallow, or steps are getting lost somewhere. A fixed home offset gets absorbed by two-star alignment, so this only matters when re-homing without realigning.

Next: laser on a wall about 3m away to see if the stage physically stops in the same spot each home. Same spot with scattered HOMED numbers means lost steps. Spot moving means the switch.

## 2026-10-05: Half-turn az cam and fixed az motor plate

Printed and installed the new az home cam. Same 18.5mm peak radius, raised section stretched to about half a turn, and the CW home ramp shortened from 65 to 20 degrees so the switch trips on a steeper part of the ramp. The other ramp stays at 65 degrees. The lever rides it smoothly in both directions by hand.

Replaced the slotted az motor plate with one that has round holes instead of slots, reusing both rails. That puts the motor shaft at a fixed 72.8mm from the center shaft: 72.5mm nominal for a GT2-250 belt on 20T and 80T pulleys, plus 0.3mm for tension. The V-notch on the plate faces away from the center shaft. Belt is snug.

Cleaned up some of the wiring.

Added the current full assembly STEP and the two new print files to `hardware/cad/`.

Expected: the new ramp is about 3x steeper where the switch trips, so if the homing scatter is coming from the switch, the ±0.38 degrees should drop to around ±0.12 and the 6 degree direction gap to about 2. Not tested yet.

Next: power up, measure the new switch window, rerun homing repeatability, then the laser wall test.

## 2026-10-05: Laser wired, az switch homing dropped

Mapped the new half-turn cam with `app/az_walk.py`. Going CCW, the switch releases cleanly off the steep ramp. Going CW back up the steep ramp, it doesn't click on until about 34 degrees onto the flat top. On the flat top the lever is pushed far enough to hold the switch on but not far enough to click it on, so the old homing routine, which expected a click on the steep ramp, got stuck. Compared the cam STEP to the previous +1.0mm cam: same 14.5/18.5mm radii, rim, height, and clamp, so the file isn't the cause. The switch is acting about half a mm farther out than with the old cam.

Rewrote `H AZ` to home on the CCW release edge instead. It works, but the HOMED numbers drifted about 70 steps when starting from off the cam. A test of plain moves (four ±3000 step round trips, then home) came back 42 steps off, within homing scatter, so normal moves aren't losing steps.

Dropped switch homing for az. It only locates the stage relative to the base, and two-star alignment handles where it points in the sky every session. The only real job left is cable management, which an index mark does. For now az zero is a pencil mark on the base and stage, lined up before power-on. Later, a penny-width slot in the turntable rim and lid will lock it in place. `H AZ` stays in the firmware as a test tool. Alt homing stays.

Wired the laser through a 2N2222: D8 to a 330 ohm resistor to the base, emitter to GND, collector to the laser's black wire, laser red to 5V. Used 330 instead of the 1k planned earlier because green diodes can pull 100+mA and 1k only switches about 25mA cleanly. `L 1` turns it on at full brightness, same as wired straight to 5V. `L 0` turns it off, and `X` kills it.

Next: laser auto-off timer, alt homing on connect in pointer.py, jog controls, two-star alignment.

## 2026-10-06: Wall test and laser auto-off

Unplugged both endstops. The firmware only reads them during H, H AZ, and E, and both pins have pull-ups, so unplugged they just read as not pressed.

Wall test with the laser on the mount, about 114.5 inches (2.91m) from the wall. 100 steps on az moved the dot 144.6mm both directions. Expected 143mm, the difference is because I measured from the laser tip, which sits a few cm in front of the az axis. 100 steps on alt moved it 142.99mm both directions, matching the expected 143mm. After repeated back-and-forth moves on both axes, including direction reversals, the dot landed back on its marks within about half a mm, which is under 0.01 degrees. Step scale is correct on both axes and backlash is too small to measure. The 6 degree gap from the old az switch tests was switch hysteresis, not the belt.

Added a laser auto-off: the laser turns off on its own 60 seconds after the last L 1. It turns off silently so the host doesn't read an unexpected line as the reply to its next command. Tested, it shuts off at about a minute.

Next: jog controls in the web app, then two-star alignment.

## 2026-10-06: First on-sky GOTO

Tested in the driveway, which slopes about 4 degrees. Startup: stage facing roughly south, laser laid flat, 12V on, then the web app.

First attempt failed because the laser wasn't flat at startup (alt zero came out 47 degrees off, outside the solver's search range), and the az stage could be turned by hand while the motor was holding. The 80T pulley wasn't gripping the center shaft. A long az slew fell short, and every move after that carried the error forward. The app was commanding the right moves, the stage just didn't follow. The earlier wall test only used short moves, so it didn't catch this. Tightened it.

Second attempt: aligned on Altair and Vega, sighting straight down the beam from behind the laser. Alignment reported the base about 3 degrees off level and alt zero within 0.1 degrees, both matching the real setup. GOTO to Deneb, Polaris, and back to Vega all landed on the star with no jog correction needed.

Lessons: 12V on before starting the app so the laser can't swing, sight down the beam when centering, and face south at startup so the cable limit sits due north where few stars cross.

Next: big round-trip az test indoors to confirm the pulley stays tight, then measure accuracy across more stars.
