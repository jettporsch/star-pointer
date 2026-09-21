from datetime import datetime, timezone

from app.mount import Mount
from app.skycoords import Observer, look_up

# 200 steps/rev x 16 microsteps x 4:1 belt, per degree of output
STEPS_PER_DEG = 200 * 16 * 4 / 360

# Which motor drives which axis, and direction. Set these once the
# mount is built: flip a sign to -1 if that axis moves backwards.
ALT_AXIS, AZ_AXIS = 1, 2
ALT_SIGN, AZ_SIGN = 1, 1

ALT_MIN, ALT_MAX = 0.0, 90.0

WYLIE = Observer(latitude_deg=33.0151, longitude_deg=-96.5389, name="Wylie, TX")


class Pointer:
    def __init__(self, mount):
        self.m = mount
        # For now, wherever the motors are at connect is alt 0, az 0,
        # and the mount must be level and facing true north.
        # Endstop homing and calibration replace this later.
        pos, _ = self.m.status()
        self.home = pos

    def _steps(self):
        pos, _ = self.m.status()
        alt = pos[ALT_AXIS - 1] - self.home[ALT_AXIS - 1]
        az = pos[AZ_AXIS - 1] - self.home[AZ_AXIS - 1]
        return alt, az

    def where(self):
        alt, az = self._steps()
        return (alt * ALT_SIGN / STEPS_PER_DEG,
                az * AZ_SIGN / STEPS_PER_DEG)

    def goto(self, alt, az, wait=True):
        if not ALT_MIN <= alt <= ALT_MAX:
            raise ValueError(f"altitude {alt} outside {ALT_MIN} to {ALT_MAX}")
        # keep azimuth in -180 to +180 so cables never wrap past the seam
        az = (az + 180) % 360 - 180

        target_alt = round(alt * STEPS_PER_DEG) * ALT_SIGN
        target_az = round(az * STEPS_PER_DEG) * AZ_SIGN
        cur_alt, cur_az = self._steps()

        # both axes start together, firmware runs them at the same time
        self.m.move(ALT_AXIS, target_alt - cur_alt)
        self.m.move(AZ_AXIS, target_az - cur_az)
        if wait:
            self.m.wait()

    def point_at(self, name, observer=WYLIE, when=None):
        when = when or datetime.now(timezone.utc)
        target = look_up(name, observer, when)
        if not target.visible:
            raise ValueError(f"{name} is below the horizon: {target}")
        self.goto(target.altitude_deg, target.azimuth_deg)
        return target
