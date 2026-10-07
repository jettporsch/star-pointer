# Serial protocol

USB serial (the Nucleo's ST-LINK virtual COM port), 115200 baud, 8N1. Commands
are plain text lines ending in CR or LF. The firmware echoes each character as
it's typed, so a terminal like `screen` works for manual testing. The Python
side skips the echo and reads the next non-empty line as the reply.

Every command gets exactly one reply line. Errors start with `ERR`. The
firmware never sends anything unprompted except `star pointer ready` at
startup, so the host can always pair a reply with the command that caused it.

Axis 1 is altitude, axis 2 is azimuth. Positive altitude raises the beam,
positive azimuth turns the stage clockwise seen from above. One step is a 1/16
microstep: 200 x 16 x 4 / 360 = 35.56 steps per degree at the output.

## Commands

| Command | Reply | What it does |
|---|---|---|
| `M <axis> <steps>` | `OK` | Relative move. Returns right away; the move runs in the background. Both axes can move at once. |
| `S` | `POS <alt> <az> BUSY <alt> <az>` | Step counts since power-on, and whether each axis is still moving (1 or 0). |
| `X` | `OK` | Stop both axes and turn the laser off. |
| `V <us>` | `OK` | Step period in microseconds, 100 to 20000, both axes. Power-on default is 600. The host sets 2000 because the loaded az stage can stall faster. |
| `L 1` | `OK` | Laser on. It turns itself off 60 s later unless `L 1` is sent again. |
| `L 0` | `OK` | Laser off. |
| `E` | `ES ALT <0/1> AZ <0/1>` | Endstop states, 1 means pressed. Reads 0 with the switches unplugged. |
| `H` | `HOMED` | Altitude homing on its endstop. Optional, see decision D7. |
| `H AZ` | `HOMED <n>` | Azimuth homing test routine. `n` is where the count thought the edge was before zeroing. Kept as a test tool. |

## Errors

| Reply | Cause |
|---|---|
| `ERR busy` | `M` sent to an axis that is still moving, or `V` sent while either axis moves |
| `ERR bad axis` | Axis not 1 or 2 |
| `ERR bad period` | `V` outside 100 to 20000 |
| `ERR unknown` | Unrecognized command |
| `ERR no switch`, `ERR no release`, `ERR no edge`, `ERR stuck on` | Homing could not find the switch edge it expected |

## Laser timeout

The 60 s auto-off is a dead-man switch. While the web page is open with the
laser on, the app re-sends `L 1` every 10 seconds. If the page, the laptop, or
the USB cable goes away, nothing re-arms it and the beam goes off on its own.
It turns off silently on purpose: an unprompted message would be read as the
reply to the host's next command.
