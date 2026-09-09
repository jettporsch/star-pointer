"""
skycoords.py - RA/Dec to Alt/Az conversion for the star pointer.

Takes a star's catalog coordinates, my location, and the current time, and
works out where the mount should point. Standard library only.

Pipeline for one target:
    catalog RA/Dec (J2000)
      -> precess to epoch of date
      -> hour angle from local sidereal time
      -> altitude / azimuth for the observer
      -> add atmospheric refraction

Sign conventions:
    latitude   +north
    longitude  +east   (Wylie, TX is about -96.5)
    azimuth    0 = true north, increasing eastward (N=0, E=90, S=180, W=270)
    altitude   0 = horizon, +90 = zenith
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

J2000 = 2451545.0
SECONDS_PER_DAY = 86400.0


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

def julian_date(when_utc: datetime) -> float:
    """
    Julian Date from a timezone-aware UTC datetime.

    Turns a calendar date into a single number, counting days elapsed since
    noon on Jan 1, 4713 BC. That start point is arbitrary, it is just what
    astronomers settled on. The reason to bother is that calendars are awkward
    for arithmetic: months have different lengths and leap years have rules
    with exceptions. Julian dates make date math subtraction.

    Anchor point: noon UTC on Jan 1, 2000 is exactly JD 2451545.0.
    """
    if when_utc.tzinfo is None:
        raise ValueError("datetime must be timezone-aware; use timezone.utc")
    t = when_utc.astimezone(timezone.utc)

    y, m = t.year, t.month
    # Jan and Feb count as months 13 and 14 of the previous year, which puts
    # leap day at the end where it does not disturb the formula
    if m <= 2:
        y -= 1
        m += 12

    a = y // 100
    b = 2 - a + a // 4  # Gregorian correction: century years are not leap
                        # years unless divisible by 400

    day_fraction = (
        t.day
        + (t.hour + t.minute / 60.0 + (t.second + t.microsecond / 1e6) / 3600.0) / 24.0
    )

    return (
        math.floor(365.25 * (y + 4716))
        + math.floor(30.6001 * (m + 1))
        + day_fraction
        + b
        - 1524.5
    )


def gmst_degrees(jd: float) -> float:
    """
    Greenwich Mean Sidereal Time in degrees.

    Which right ascension is currently crossing overhead at Greenwich.

    The key number is 360.98564736629, the degrees the sky turns per day. It
    is not 360 because the extra 0.986 is Earth's daily orbital motion around
    the Sun. That is the four minute difference between a solar day and a
    sidereal day. The remaining terms are small long-term corrections.

    Formula from Meeus, Astronomical Algorithms.
    """
    d = jd - J2000
    t = d / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * d
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )
    return gmst % 360.0


def lst_degrees(jd: float, longitude_deg: float) -> float:
    """
    Local Mean Sidereal Time in degrees.

    Greenwich sidereal time plus my longitude. I am 96.5 degrees west, so I
    see a given star about 6.4 hours after Greenwich does. Longitude is
    positive east, so Texas is negative.
    """
    return (gmst_degrees(jd) + longitude_deg) % 360.0


# ---------------------------------------------------------------------------
# Precession (J2000 -> epoch of date)
# ---------------------------------------------------------------------------

def precess_from_j2000(ra_deg: float, dec_deg: float, jd: float) -> tuple[float, float]:
    """
    Rotate J2000 catalog coordinates to the mean equinox of date.

    Catalog coordinates are frozen at the year 2000. Earth's axis wobbles like
    a slow spinning top, one full circle every 26,000 years, so the coordinate
    grid itself drifts and a star's listed position goes stale. It is not
    wrong, it is correct for 2000 and out of date for now.

    26 years of drift is 0.15 to 0.37 degrees depending on where the star
    sits, which against a +/-0.5 degree budget takes up most of it.

    The three angles zeta, z and theta describe how much the grid rotated.
    This function applies that rotation. The numbers are the IAU 1976 model.
    """
    t = (jd - J2000) / 36525.0

    zeta = math.radians(0.6406161 * t + 0.0000839 * t * t + 0.0000050 * t ** 3)
    z = math.radians(0.6406161 * t + 0.0003041 * t * t + 0.0000051 * t ** 3)
    theta = math.radians(0.5567530 * t - 0.0001185 * t * t - 0.0000116 * t ** 3)

    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)

    a = math.cos(dec) * math.sin(ra + zeta)
    b = (
        math.cos(theta) * math.cos(dec) * math.cos(ra + zeta)
        - math.sin(theta) * math.sin(dec)
    )
    c = (
        math.sin(theta) * math.cos(dec) * math.cos(ra + zeta)
        + math.cos(theta) * math.sin(dec)
    )

    ra_out = math.degrees(math.atan2(a, b) + z) % 360.0
    dec_out = math.degrees(math.asin(max(-1.0, min(1.0, c))))
    return ra_out, dec_out


# ---------------------------------------------------------------------------
# Refraction
# ---------------------------------------------------------------------------

def refraction_degrees(apparent_alt_deg: float) -> float:
    """
    Atmospheric refraction, in degrees.

    The atmosphere bends starlight as it enters, so stars look higher than
    they actually are. Half a degree at the horizon, about 0.02 degrees at 45
    degrees altitude, essentially nothing overhead.

    Half a degree is the width of the full moon. When you watch a sunset, the
    Sun has already geometrically set by the time you see it touch the
    horizon.

    Bennett's formula is an empirical fit, not derived from physics. Returns 0
    below the horizon.
    """
    if apparent_alt_deg < -1.0:
        return 0.0
    h = apparent_alt_deg
    arcmin = 1.0 / math.tan(math.radians(h + 7.31 / (h + 4.4)))
    return arcmin / 60.0


# ---------------------------------------------------------------------------
# Observer and the main transform
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observer:
    latitude_deg: float      # +north
    longitude_deg: float     # +east
    name: str = ""


@dataclass(frozen=True)
class Target:
    altitude_deg: float
    azimuth_deg: float

    @property
    def visible(self) -> bool:
        return self.altitude_deg > 0.0

    def __str__(self) -> str:
        state = "up" if self.visible else "below horizon"
        return f"alt {self.altitude_deg:+7.3f}  az {self.azimuth_deg:7.3f}  ({state})"


def radec_to_altaz(
    ra_deg: float,
    dec_deg: float,
    observer: Observer,
    when_utc: datetime,
    apply_precession: bool = True,
    apply_refraction: bool = True,
) -> Target:
    """
    Convert J2000 RA/Dec to altitude and azimuth. The main event.

    Runs the pipeline: precess, compute hour angle, apply the spherical trig,
    add refraction.

    Hour angle is LST minus RA, meaning how far past overhead the star is.
    Zero means it is crossing my meridian right now, at its highest.

    The altitude line is the triangle formed by the celestial pole, my zenith,
    and the star. Three sides are known, solve for the fourth.

    Azimuth is the same triangle solved for the angle at the zenith instead.
    It uses atan2 rather than atan because atan2 looks at the signs of both
    inputs to pick the right quadrant, giving the full 0 to 360 range.
    """
    jd = julian_date(when_utc)

    if apply_precession:
        ra_deg, dec_deg = precess_from_j2000(ra_deg, dec_deg, jd)

    lst = lst_degrees(jd, observer.longitude_deg)
    hour_angle = math.radians((lst - ra_deg) % 360.0)

    dec = math.radians(dec_deg)
    lat = math.radians(observer.latitude_deg)

    sin_alt = (
        math.sin(dec) * math.sin(lat)
        + math.cos(dec) * math.cos(lat) * math.cos(hour_angle)
    )
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))

    az = math.atan2(
        -math.sin(hour_angle) * math.cos(dec),
        math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(hour_angle),
    )

    alt_deg = math.degrees(alt)
    az_deg = math.degrees(az) % 360.0

    if apply_refraction:
        alt_deg += refraction_degrees(alt_deg)

    return Target(alt_deg, az_deg)


# ---------------------------------------------------------------------------
# 22 bright stars with J2000 coordinates, including all seven Big Dipper
# stars. Hardcoded because 22 entries does not justify a file format.
# ---------------------------------------------------------------------------

CATALOG: dict[str, tuple[float, float]] = {
    # name:            (RA deg,   Dec deg)
    "Polaris":         (37.95456,  89.26411),
    "Vega":            (279.23473, 38.78369),
    "Sirius":          (101.28716, -16.71612),
    "Arcturus":        (213.91530, 19.18241),
    "Capella":         (79.17233,  45.99799),
    "Rigel":           (78.63447, -8.20164),
    "Procyon":         (114.82550, 5.22499),
    "Betelgeuse":      (88.79294,  7.40706),
    "Altair":          (297.69582, 8.86832),
    "Aldebaran":       (68.98016,  16.50930),
    "Antares":         (247.35191, -26.43200),
    "Spica":           (201.29825, -11.16132),
    "Pollux":          (116.32896, 28.02620),
    "Deneb":           (310.35798, 45.28034),
    "Regulus":         (152.09296, 11.96721),
    # Big Dipper, west to east
    "Dubhe":           (165.93196, 61.75103),
    "Merak":           (165.46032, 56.38243),
    "Phecda":          (178.45771, 53.69476),
    "Megrez":          (183.85650, 57.03262),
    "Alioth":          (193.50729, 55.95982),
    "Mizar":           (200.98142, 54.92536),
    "Alkaid":          (206.88516, 49.31327),
}


def look_up(name: str, observer: Observer, when_utc: datetime) -> Target:
    """
    Convenience wrapper. Takes a name like "Vega", looks the coordinates up in
    the catalog dict, and calls the transform.
    """
    key = name.strip().title()
    if key not in CATALOG:
        raise KeyError(f"{name!r} not in catalog. Known: {', '.join(sorted(CATALOG))}")
    ra, dec = CATALOG[key]
    return radec_to_altaz(ra, dec, observer, when_utc)


if __name__ == "__main__":
    wylie = Observer(latitude_deg=33.0151, longitude_deg=-96.5389, name="Wylie, TX")
    now = datetime.now(timezone.utc)

    print(f"{wylie.name}  {now.isoformat(timespec='seconds')}")
    print(f"LST = {lst_degrees(julian_date(now), wylie.longitude_deg):.3f} deg\n")

    for star in sorted(CATALOG):
        print(f"  {star:<12} {look_up(star, wylie, now)}")
