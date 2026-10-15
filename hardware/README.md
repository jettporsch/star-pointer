Parts list in `bom.md`, measured part dimensions in `dimensions.md`, and a dated
log of every bench test in `bench-notes.md`.

CAD files in `cad/`. `v2/` is the current mount: print files, editable STEP,
the full assembly, and a parts and fastener list in its README. `v1/` has the
prototype assembly and the last two parts revised on it.

## Wiring

The electronics are on a half breadboard inside the base. No PCB yet.

| Nucleo pin | Header | Goes to |
|---|---|---|
| PB4 (TIM3 CH1) | D5 | Altitude driver STEP |
| PB5 | D4 | Altitude driver DIR |
| PB10 (TIM2 CH3) | D6 | Azimuth driver STEP |
| PA8 | D7 | Azimuth driver DIR |
| PA9 | D8 | 330 Ω to the 2N2222 base (laser) |
| 3V3 | | Driver logic rail |
| 5V | | Laser + |
| GND | | Common ground |

Each DRV8825: M0 and M1 to GND and M2 to 3.3 V for 1/16 microstepping, RST
jumpered to SLP and SLP to 3.3 V, VMOT to 12 V with a 100 µF cap at the pin.
The motor plug covers B2, B1, A1, A2, the middle four pins on the motor side.
From the VMOT end the wire order is red, green, black, blue.

The laser's black lead goes to the 2N2222 collector, emitter to ground.
