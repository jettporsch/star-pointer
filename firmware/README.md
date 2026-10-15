STM32 firmware for a Nucleo-F401RE. Toolchain: STM32CubeIDE.

Takes step moves over USB serial, runs both axes from hardware timers, and
switches the laser. Command set is in `docs/serial-protocol.md`, pin map in
`hardware/README.md`.

Each STEP pin is a timer channel in PWM mode: TIM3 CH1 for altitude, TIM2 CH3
for azimuth. The auto-reload sets the step period and the compare is half of
it, so each timer cycle is one step pulse. An interrupt counts pulses and stops
the timer when the move is done.

## Build and flash

1. Open `star-pointer-fw` in STM32CubeIDE (File > Open Projects from File
   System).
2. Plug in the Nucleo's USB and click Run. It builds, flashes over the onboard
   ST-Link, and starts.
3. The board prints `star pointer ready` on its serial port at 115200 baud.

The firmware stays on the board, so this is only needed after changing it.
