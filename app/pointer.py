import math
from datetime import datetime, timezone

from app.align import Alignment, separation, vec
from app.mount import Mount
from app.skycoords import Observer, look_up

# 200 steps/rev x 16 microsteps x 4:1 belt, per degree of output
STEPS_PER_DEG = 200 * 16 * 4 / 360

# Which motor drives which axis, and direction. Checked on the bench:
# +alt moves the beam up, +az turns the stage CW from above.
ALT_AXIS, AZ_AXIS = 1, 2
ALT_SIGN, AZ_SIGN = 1, 1

ALT_MIN, ALT_MAX = 0.0, 90.0

WYLIE = Observer(latitude_deg=33.0151, longitude_deg=-96.5389, name="Wylie, TX")


class Pointer:
    def __init__(self, mount):
        self.m = mount
        # Raw zero is wherever the motors are at connect: stage on the pencil
        # mark, laser resting roughly flat. Two-star alignment works out how
        # that relates to the sky.
        pos, _ = self.m.status()
        self.home = pos
        self.align = Alignment()

    def _steps(self):
        pos, _ = self.m.status()
        alt = pos[ALT_AXIS - 1] - self.home[ALT_AXIS - 1]
        az = pos[AZ_AXIS - 1] - self.home[AZ_AXIS - 1]
        return alt, az

    def where_raw(self):
        """Mount angles from step counts, relative to the power-on position."""
        alt, az = self._steps()
        return (alt * ALT_SIGN / STEPS_PER_DEG,
                az * AZ_SIGN / STEPS_PER_DEG)

    def where(self):
        """Where in the sky the beam is pointing, using the current alignment."""
        return self.align.to_sky(*self.where_raw())

    def goto_raw(self, raw_alt, raw_az, wait=True):
        # keep raw azimuth within half a turn of the pencil mark so the
        # cables never wind past their slack
        raw_az = (raw_az + 180) % 360 - 180

        target_alt = round(raw_alt * STEPS_PER_DEG) * ALT_SIGN
        target_az = round(raw_az * STEPS_PER_DEG) * AZ_SIGN
        cur_alt, cur_az = self._steps()

        # both axes start together, firmware runs them at the same time
        self.m.move(ALT_AXIS, target_alt - cur_alt)
        self.m.move(AZ_AXIS, target_az - cur_az)
        if wait:
            self.m.wait()

    def goto(self, alt, az, wait=True):
        """Point at a sky altitude/azimuth, corrected by the alignment."""
        if not ALT_MIN <= alt <= ALT_MAX:
            raise ValueError(f"altitude {alt} outside {ALT_MIN} to {ALT_MAX}")
        self.goto_raw(*self.align.to_mount(alt, az), wait=wait)

    def record_star(self, name, observer=WYLIE, when=None):
        """Call with the beam centered on `name`. Returns the alignment report."""
        when = when or datetime.now(timezone.utc)
        target = look_up(name, observer, when)
        if not target.visible:
            raise ValueError(f"{name} is below the horizon")
        raw_alt, raw_az = self.where_raw()
        return self.align.add(name, target.altitude_deg, target.azimuth_deg,
                              raw_alt, raw_az)

    def point_at(self, name, observer=WYLIE, when=None):
        when = when or datetime.now(timezone.utc)
        target = look_up(name, observer, when)
        if not target.visible:
            raise ValueError(f"{name} is below the horizon: {target}")
        self.goto(target.altitude_deg, target.azimuth_deg)
        return target

    def miss(self, name, observer=WYLIE, when=None):
        """Call after a GOTO, once the beam has been jogged onto `name`.

        Compares the star's real position with where the alignment thinks the
        beam is now. That difference is how far the GOTO landed from the star.
        Uses the star's position right now, so time spent jogging doesn't count
        against the result even though the sky keeps moving.
        """
        when = when or datetime.now(timezone.utc)
        star = look_up(name, observer, when)
        beam_alt, beam_az = self.where()
        up = beam_alt - star.altitude_deg
        right = ((beam_az - star.azimuth_deg + 180) % 360 - 180) * math.cos(
            math.radians(star.altitude_deg))
        total = separation(vec(beam_alt, beam_az),
                           vec(star.altitude_deg, star.azimuth_deg))
        # The beam is on the star now, so the alignment's error here is the
        # GOTO's miss with the sign flipped: positive means it landed high/right.
        return {"star": name, "alt": star.altitude_deg, "az": star.azimuth_deg,
                "up": -up, "right": -right, "total": total}
