# Bill of materials

## Ordered

| Qty | Item | Spec | Source |
|---|---|---|---|
| 1 | STM32 Nucleo-F401RE | STM32F401RET6, onboard ST-Link | DigiKey |
| 4 | 100 µF 50 V electrolytic | Panasonic EEU-FR1H101B, low ESR | DigiKey |
| 10 | 0.1 µF 50 V X7R ceramic | Kemet C320C104K5R5TA, 2.54 mm pitch | DigiKey |
| 2 | 470 µF 35 V electrolytic | Panasonic EEU-FM1V471 | DigiKey |
| 3 | NEMA 17 stepper | 1.5 A, 42 N·cm, 42x42x38 mm | Amazon |
| 5 | DRV8825 driver module | With heatsink | Amazon |
| 6 | GT2 pulley, 20T | 5 mm bore, 6 mm belt | Amazon |
| 1 | GT2 pulley kit, 20T and 80T | 8 mm bore, with 250 mm belts | Amazon |
| 5 | GT2 closed loop belt | 110/200/300/400/610 mm, 6 mm wide | Amazon |
| 5 | Mechanical endstop | 3-pin, with LED and pull-up | Amazon |
| 1 | 12 V 5 A power supply | 5.5x2.1 mm barrel, screw terminal adapter | Amazon |
| 6 | LM2596 buck converter | Adjustable, 3 A | Amazon |
| 10 | 608-2RS bearing | 8x22x7 mm | Amazon |
| 1 | Lazy susan bearing | 4 inch aluminum | Amazon |
| 2 | Linear shaft | 8 mm x 400 mm hardened steel | Amazon |
| 1 | M3 hardware assortment | 6 to 30 mm, nuts and washers | Amazon |
| 1 | Breadboard and jumper kit | 830 tie points | Amazon |
| 1 | Multimeter | Klein MM325, CAT III 600 V | Amazon |

## Still to order

| Item | Notes |
|---|---|
| Green laser module | 5 mW, Class 3R |
| MOSFET and gate resistor | Laser switching |
| Momentary pushbutton | Dead-man switch |
| PCB fabrication | After the breadboard design is proven |
| Camera tripod | Any 1/4-20 tripod works as the base |

## Notes

**Power.** 12 V for the motor rail, 5 V stepped down for logic, common ground.
The 100 µF bulk cap goes physically at each driver's VMOT pin, not somewhere
convenient on the rail. The DRV8825 datasheet is explicit about this and
skipping it is a known way to kill the driver.

**Current limit.** Set Vref before connecting a motor. My motors are rated
1.5 A but the DRV8825 with a stick-on heatsink handles about 1.5 A at best, and
this application has almost no load, so around 1 A is the target. Getting it
wrong overheats the motor and causes missed steps, which will look like a
firmware bug and waste a day.

**Laser safety.** Class 3R green is the astronomy standard. Planned interlocks:
momentary dead-man switch, firmware timeout, laser disabled while slewing, and
a minimum altitude cutoff. Pointing a laser at aircraft is a federal offense,
so this does not get operated near an approach path.
