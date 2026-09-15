# Bench Notes

## 2026-09-15: First stepper test

The motor is rated at 1.5A. Coil pairs are black/blue and green/red.

The driver is a DRV8825 with R100 sense resistors, so I = Vref × 2. I set Vref to 0.595V, which is about 1.19A, 80% of the rating.

SLEEP floated low on this board, so SLEEP and RESET are tied to 3V3 on the Nucleo.

STEP is on PB4 and DIR is on PB5.

I tested one revolution forward and back at 5ms per step, and it worked.

The only problem I hit was that SLEEP floated low, which kept Vref reading 0 until it was tied to 3V3.
