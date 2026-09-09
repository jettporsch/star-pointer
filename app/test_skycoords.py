"""
test_skycoords.py - validate the transform against physical facts.

The transform is checked against physical facts rather than against another
library. If a check fails, its name points at the specific thing that broke.
Comparing to a reference implementation would only tell me the two disagree,
not where or which one is wrong.

Run:  python3 test_skycoords.py
"""

import math
from datetime import datetime, timedelta, timezone

from skycoords import (
    CATALOG,
    Observer,
    julian_date,
    gmst_degrees,
    lst_degrees,
    radec_to_altaz,
    refraction_degrees,
)

WYLIE = Observer(latitude_deg=33.0151, longitude_deg=-96.5389, name="Wylie, TX")

_failures = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"   {detail}" if detail else ""))
    if not condition:
        _failures.append(name)


def angular_sep(alt1, az1, alt2, az2):
    """Great-circle separation between two alt/az points, in degrees."""
    a1, a2 = math.radians(alt1), math.radians(alt2)
    dz = math.radians(az1 - az2)
    cos_sep = math.sin(a1) * math.sin(a2) + math.cos(a1) * math.cos(a2) * math.cos(dz)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))


print("\n--- Time ---")

# Known anchor: 2000-01-01 12:00 UTC is exactly JD 2451545.0 by definition.
jd = julian_date(datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
check("J2000 epoch maps to JD 2451545.0", abs(jd - 2451545.0) < 1e-9, f"got {jd}")

# One sidereal day is 23h56m04.09s, so GMST must advance ~360 deg in that span.
t0 = datetime(2026, 9, 9, 0, 0, 0, tzinfo=timezone.utc)
sidereal_day = timedelta(seconds=86164.0905)
drift = (gmst_degrees(julian_date(t0 + sidereal_day)) - gmst_degrees(julian_date(t0))) % 360.0
drift = min(drift, 360.0 - drift)
check("GMST advances 360 deg per sidereal day", drift < 0.001, f"residual {drift:.6f} deg")

# LST is GMST offset by longitude.
lst = lst_degrees(julian_date(t0), WYLIE.longitude_deg)
expected = (gmst_degrees(julian_date(t0)) + WYLIE.longitude_deg) % 360.0
check("LST applies longitude offset", abs(lst - expected) < 1e-9)


print("\n--- Geometry ---")

# Polaris sits close to the celestial pole, so its altitude equals my latitude
# and it barely moves all night. Checked at eight times.
#
# Traps latitude handling. If that is broken this fails and almost nothing else
# explains it.
#
# The 1 deg tolerance is not slop in the code. Polaris is 0.74 deg off the true
# pole, so the measured error should sit just under that.
worst_alt_err = 0.0
worst_az_err = 0.0
for hours in range(0, 24, 2):
    t = t0 + timedelta(hours=hours)
    p = radec_to_altaz(*CATALOG["Polaris"], WYLIE, t, apply_refraction=False)
    worst_alt_err = max(worst_alt_err, abs(p.altitude_deg - WYLIE.latitude_deg))
    az_err = min(p.azimuth_deg, 360.0 - p.azimuth_deg)
    worst_az_err = max(worst_az_err, az_err)

check("Polaris altitude tracks latitude", worst_alt_err < 1.0, f"max err {worst_alt_err:.3f} deg")
check("Polaris stays near true north", worst_az_err < 2.0, f"max az off N {worst_az_err:.3f} deg")

# A star at declination 33 seen from 33 deg north passes directly overhead once
# per day. Traps errors in how declination feeds the transform. 90 is a hard
# number, not an approximation.
#
# Precession is off for this one. With it on, the declination gets nudged about
# 0.2 deg away from my latitude and the star no longer hits the zenith exactly,
# so the check would fail for a reason unrelated to the bug it looks for.
# Sampled coarse then refined: the altitude peak at the zenith is a cusp, not a
# smooth maximum, so sampling error shrinks linearly and a coarse grid alone
# leaves ~0.1 deg on the table.
def peak_altitude(ra, dec, start, span_s, step_s, precess=False):
    best, best_t = -90.0, start
    n = int(span_s / step_s)
    for i in range(n + 1):
        t = start + timedelta(seconds=i * step_s)
        a = radec_to_altaz(ra, dec, WYLIE, t,
                           apply_precession=precess, apply_refraction=False).altitude_deg
        if a > best:
            best, best_t = a, t
    return best, best_t

_, coarse_t = peak_altitude(120.0, WYLIE.latitude_deg, t0, 86400, 60)
peak, _ = peak_altitude(120.0, WYLIE.latitude_deg, coarse_t - timedelta(seconds=90), 180, 0.05)
check("dec == latitude transits the zenith", abs(peak - 90.0) < 0.01, f"peak alt {peak:.4f} deg")

# Culmination happens when local sidereal time equals the star's RA.
ra, dec = CATALOG["Vega"]
best_alt, best_t = -90.0, None
for minutes in range(0, 1440):
    t = t0 + timedelta(minutes=minutes)
    a = radec_to_altaz(ra, dec, WYLIE, t, apply_refraction=False).altitude_deg
    if a > best_alt:
        best_alt, best_t = a, t
ha_at_peak = (lst_degrees(julian_date(best_t), WYLIE.longitude_deg) - ra) % 360.0
ha_at_peak = min(ha_at_peak, 360.0 - ha_at_peak)
check("Vega culminates when LST == RA", ha_at_peak < 0.5, f"hour angle {ha_at_peak:.3f} deg")

# Max altitude at culmination must be 90 - |lat - dec|.
predicted = 90.0 - abs(WYLIE.latitude_deg - dec)
check("culmination altitude matches 90-|lat-dec|",
      abs(best_alt - predicted) < 0.5,
      f"got {best_alt:.3f}, predicted {predicted:.3f}")

# Southern star well below the southern horizon limit should never rise here.
never_up = radec_to_altaz(50.0, -80.0, WYLIE, t0, apply_refraction=False)
check("far-south star is below horizon", not never_up.visible,
      f"alt {never_up.altitude_deg:.2f}")

# Mizar and Alkaid are two stars in the Big Dipper's handle, 6.676 deg apart.
# That distance is fixed. As the night goes on both stars' altitude and azimuth
# change constantly, but the gap between them does not.
#
# This computes both positions at eight times across a day and measures the
# separation each time. The spread should be zero.
#
# Traps anything that is not a proper rotation, since a proper rotation
# preserves distance. A sign error or a swapped sine and cosine would skew the
# sky instead of rotating it, and this catches that even when every
# single-star check passes.
mizar, alkaid = CATALOG["Mizar"], CATALOG["Alkaid"]
seps = []
for hours in range(0, 24, 3):
    t = t0 + timedelta(hours=hours)
    m = radec_to_altaz(*mizar, WYLIE, t, apply_refraction=False)
    a = radec_to_altaz(*alkaid, WYLIE, t, apply_refraction=False)
    seps.append(angular_sep(m.altitude_deg, m.azimuth_deg, a.altitude_deg, a.azimuth_deg))
spread = max(seps) - min(seps)
check("Mizar-Alkaid separation is rotation-invariant", spread < 0.01,
      f"spread {spread:.6f} deg, sep {seps[0]:.3f} deg")


print("\n--- Corrections ---")

# This one is not checking correctness. It runs every catalog star twice, once
# with precession applied and once without, and measures how far apart the two
# answers land.
#
# It confirms the correction is worth applying. Against my +/-0.5 deg budget
# the shift is most of it, so the correction stays.
t_now = datetime(2026, 9, 9, 4, 0, 0, tzinfo=timezone.utc)
shifts = []
for ra, dec in CATALOG.values():
    a = radec_to_altaz(ra, dec, WYLIE, t_now, apply_precession=True, apply_refraction=False)
    b = radec_to_altaz(ra, dec, WYLIE, t_now, apply_precession=False, apply_refraction=False)
    shifts.append(angular_sep(a.altitude_deg, a.azimuth_deg, b.altitude_deg, b.azimuth_deg))
check("precession matters at the 0.1-0.5 deg level",
      0.10 < min(shifts) and 0.25 < max(shifts) < 0.50,
      f"min {min(shifts):.3f}, max {max(shifts):.3f} deg")

check("refraction near horizon is ~0.5 deg", 0.4 < refraction_degrees(0.0) < 0.6,
      f"{refraction_degrees(0.0):.3f} deg")
check("refraction at 45 deg is small", refraction_degrees(45.0) < 0.03,
      f"{refraction_degrees(45.0):.4f} deg")
check("refraction always lifts the star", refraction_degrees(10.0) > 0)


print("\n" + "=" * 52)
if _failures:
    print(f"{len(_failures)} FAILED: {', '.join(_failures)}")
    raise SystemExit(1)
print("All checks passed.")
