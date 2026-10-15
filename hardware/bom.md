# Bill of materials

Parts in the current v2 build. Printed parts and every screw, nut and washer
are listed in [`cad/v2/README.md`](cad/v2/README.md).

## Electronics

| Qty | Item | Spec | Notes |
|---|---|---|---|
| 1 | STM32 Nucleo-F401RE | STM32F401RET6, onboard ST-Link | Powered from the laptop's USB |
| 2 | DRV8825 driver module | With heatsink | Vref 0.60 V, about 1.2 A |
| 2 | NEMA 17 stepper | 1.5 A, 42 N·cm, 42x42x38 mm | |
| 2 | 100 µF 50 V electrolytic | Panasonic EEU-FR1H101B, low ESR | One at each driver's VMOT pin |
| 1 | 12 V 5 A power supply | 5.5x2.1 mm barrel, screw terminal adapter | Motors only |
| 1 | Green laser module | 5 mW, 520 nm, 12 mm x 38 mm, 3 to 5 V | Class 3R |
| 1 | 2N2222 NPN transistor | | Switches the laser from PA9 |
| 1 | 330 Ω resistor | | Transistor base |
| 1 | Half breadboard | 400 tie points | |
| | 22 AWG solid wire | | Breadboard wiring |
| | 22 AWG stranded wire | | Laser run through the cable loop |

## Mechanical

| Qty | Item | Spec | Notes |
|---|---|---|---|
| 2 | GT2 pulley, 20T | 5 mm bore, 6 mm belt | Motor side |
| 2 | GT2 pulley, 80T | 8 mm bore | Output side |
| 1 | GT2 closed belt | 250 mm, 6 mm wide | Azimuth |
| 1 | GT2 closed belt | 280 mm, 6 mm wide | Altitude |
| 2 | 608-2RS bearing | 8x22x7 mm | Altitude axis |
| 1 | Lazy susan bearing | 4 inch aluminum | Azimuth |
| 2 | 8 mm hardened rod | Cut from 400 mm stock | Altitude and azimuth shafts |
| | PLA | Navy, grey, gold | Bambu P2S |

## Bought, not in the current build

| Item | Why |
|---|---|
| Mechanical endstops | Switch homing was built and tested, then dropped (decision D7) |
| LM2596 buck converters | Not needed: the Nucleo runs from USB and supplies 5 V for the laser |
| 470 µF and 0.1 µF capacitors | Only the 100 µF bulk caps ended up on the board |
| Extra NEMA 17 and DRV8825s | Spares |
| 830-point breadboard and jumper kit | v1 wiring |
| Camera tripod (planned) | v2 has its own legs |

## Still to do

| Item | Notes |
|---|---|
| PCB | Move the breadboard circuit to a KiCad board |

## Notes

**Power.** 12 V feeds only the motor drivers. The Nucleo runs from the
laptop's USB and supplies 3.3 V for the driver logic and 5 V for the laser.
Everything shares one ground. The 100 µF bulk cap sits right at each driver's
VMOT pin, not somewhere convenient on the rail. The DRV8825 datasheet is
explicit about this, and skipping it is a known way to kill the driver.

**Current limit.** Vref is set before a motor is connected. These drivers use
0.1 Ω sense resistors, so current is Vref x 2: 0.595 V and 0.603 V give about
1.2 A, 80% of the motors' 1.5 A rating. Too much current overheats the motor
and causes missed steps, which look like a firmware bug.

**Laser safety.** Class 3R green is the astronomy standard. The firmware turns
the laser off 60 seconds after the last `L 1`, and the web app only keeps
re-arming it while the page is open, so a closed laptop or pulled cable kills
the beam. Stop and closing the app also turn it off. Pointing a laser at
aircraft is a federal offense, so this doesn't get used near an approach path.
