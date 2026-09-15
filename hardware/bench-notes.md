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
