"""Two-star alignment for an alt-az mount.

The mount reports "raw" angles from its step counts: az zero is wherever the
pencil mark was at power-on, alt zero is wherever the laser was resting.
Three unknowns separate raw angles from the real sky:

  1. az offset   which way the pencil mark actually faces
  2. base tilt   how far off level the base is (two angles)
  3. alt index   how far off flat the laser was at power-on

Center the beam on a known star, record it, do it again on a second star.

  alt index: azimuth zero and base tilt don't change the angle between two
      stars as the mount sees them, but alt index does. So we pick the alt
      index that makes the mount's angle between the stars match the sky's.

  rotation: with alt index fixed, both stars give a vector in the sky frame
      and in the mount frame. Two vectors pin down a rotation, which carries
      az offset and base tilt together (TRIAD method, same idea as Toshimi
      Taki's matrix method for telescope mounts).

One star only fixes az offset and alt index, assuming the base is level.
Good enough to slew close to the second star.

Pure Python, no numpy, so it runs anywhere the rest of the app runs.
"""
import math


# ---- small vector helpers -------------------------------------------------

def vec(alt, az):
    a, z = math.radians(alt), math.radians(az)
    return (math.cos(a) * math.cos(z), math.cos(a) * math.sin(z), math.sin(a))


def angles(v):
    n = math.sqrt(sum(c * c for c in v))
    x, y, z = (c / n for c in v)
    return (math.degrees(math.asin(max(-1.0, min(1.0, z)))),
            math.degrees(math.atan2(y, x)))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def unit(v):
    n = math.sqrt(dot(v, v))
    return tuple(c / n for c in v)


def separation(u, w):
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(u, w)))))


def mat_vec(m, v):
    return tuple(dot(row, v) for row in m)


def transpose(m):
    return tuple(zip(*m))


def mat_mul(a, b):
    bt = transpose(b)
    return tuple(tuple(dot(row, col) for col in bt) for row in a)


def triad(a, b):
    """Orthonormal frame from two directions, as a matrix with frame vectors as columns."""
    t1 = unit(a)
    t2 = unit(cross(a, b))
    t3 = cross(t1, t2)
    return transpose((t1, t2, t3))


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


# ---- alignment ------------------------------------------------------------

class Alignment:
    def __init__(self):
        self.reset()

    def reset(self):
        self.stars = []          # (name, sky_alt, sky_az, raw_alt, raw_az)
        self.R = IDENTITY        # sky vector -> mount vector
        self.alt_index = 0.0     # true mount alt = raw alt + alt_index
        self.report = "not aligned"

    def add(self, name, sky_alt, sky_az, raw_alt, raw_az):
        """Record a star the beam is centered on. Keeps the two most recent."""
        self.stars = [s for s in self.stars if s[0] != name]
        self.stars.append((name, sky_alt, sky_az, raw_alt, raw_az))
        self.stars = self.stars[-2:]
        self._solve()
        return self.report

    def _solve(self):
        if len(self.stars) == 1:
            _, s_alt, s_az, r_alt, r_az = self.stars[0]
            self.alt_index = s_alt - r_alt
            self.R = rot_z(r_az - s_az)
            self.report = (f"1 star ({self.stars[0][0]}): assuming level base, "
                           f"alt zero off by {self.alt_index:+.2f} deg")
            return

        (n1, sa1, sz1, ra1, rz1), (n2, sa2, sz2, ra2, rz2) = self.stars
        u1, u2 = vec(sa1, sz1), vec(sa2, sz2)
        sky_sep = separation(u1, u2)
        if sky_sep < 30:
            self.stars = self.stars[:1]
            self._solve()
            raise ValueError(f"{n1} and {n2} are only {sky_sep:.0f} deg apart, "
                             "pick stars at least 30 deg apart")

        def mismatch(e):
            return separation(vec(ra1 + e, rz1), vec(ra2 + e, rz2)) - sky_sep

        # Each star on its own gives a guess for alt index (sky alt minus raw
        # alt), off only by however much the base is tilted. So the true value
        # is near their average no matter how the laser was resting at power-on.
        # Scan 20 deg either side of that guess, refine every sign change by
        # bisection, and keep the root closest to the guess.
        guess = ((sa1 - ra1) + (sa2 - ra2)) / 2
        grid = [guess + i / 10 for i in range(-200, 201)]
        vals = [mismatch(e) for e in grid]
        roots = []
        for i in range(len(grid) - 1):
            if vals[i] == 0 or vals[i] * vals[i + 1] < 0:
                lo, hi = grid[i], grid[i + 1]
                for _ in range(50):
                    mid = (lo + hi) / 2
                    if mismatch(lo) * mismatch(mid) <= 0:
                        hi = mid
                    else:
                        lo = mid
                roots.append((lo + hi) / 2)
        if roots:
            e = min(roots, key=lambda r: abs(r - guess))
            residual = 0.0
        else:
            # measurement noise can leave a near-miss with no exact root
            i = min(range(len(grid)), key=lambda k: abs(vals[k]))
            e, residual = grid[i], abs(vals[i])
            if residual > 1.0:
                self.stars = self.stars[-1:]
                self._solve()
                raise ValueError(
                    f"stars don't fit by {residual:.1f} deg. Wrong star picked, "
                    "or the mount got bumped. Kept only the last star.")

        w1, w2 = vec(ra1 + e, rz1), vec(ra2 + e, rz2)
        self.alt_index = e
        self.R = mat_mul(triad(w1, w2), transpose(triad(u1, u2)))

        # base tilt: angle between the mount's vertical axis and true zenith
        mount_up_in_sky = mat_vec(transpose(self.R), (0.0, 0.0, 1.0))
        tilt = separation(mount_up_in_sky, (0.0, 0.0, 1.0))
        self.report = (f"2 stars ({n1}, {n2}): base off level {tilt:.2f} deg, "
                       f"alt zero off by {e:+.2f} deg"
                       + (f", fit residual {residual:.2f} deg" if residual else ""))

    def to_mount(self, sky_alt, sky_az):
        """Sky alt/az -> raw mount alt/az (degrees)."""
        m_alt, m_az = angles(mat_vec(self.R, vec(sky_alt, sky_az)))
        return m_alt - self.alt_index, m_az

    def to_sky(self, raw_alt, raw_az):
        """Raw mount alt/az -> where in the sky the beam is pointing."""
        return angles(mat_vec(transpose(self.R), vec(raw_alt + self.alt_index, raw_az)))


# ---- choosing a good second star ------------------------------------------

_SKY_GRID = [(alt, az) for alt in (25, 45, 65, 80) for az in range(0, 360, 30)]


def pair_sensitivity(first, second, slip=0.1):
    """How badly a centering slip on `second` throws off GOTOs elsewhere.

    `first` and `second` are sky (alt, az). Simulates a perfectly set up mount,
    aligns on both stars with `second` centered `slip` degrees off in each of
    four directions, and returns the worst GOTO error across the sky. Some pairs
    turn a 0.1 deg slip into 0.1 deg of error; others turn it into several
    degrees, mostly because the stars give the solver little to work with.
    Returns None if the pair is too close together to align on at all.
    """
    if separation(vec(*first), vec(*second)) < 30:
        return None
    worst = 0.0
    for d_alt, d_az in ((slip, 0), (-slip, 0), (0, slip), (0, -slip)):
        a = Alignment()
        a.add("first", *first, *first)
        try:
            a.add("second", *second, second[0] + d_alt, second[1] + d_az)
        except ValueError:
            return None
        for alt, az in _SKY_GRID:
            worst = max(worst, separation(vec(*a.to_mount(alt, az)), vec(alt, az)))
    return worst


# ---- desk test ------------------------------------------------------------

def _self_test():
    """Fake a badly set-up mount, align on two stars, check a third."""
    import random
    random.seed(1)

    tilt_axis, tilt, az_offset = 40.0, 3.0, 137.0

    # true sky -> mount: tilt the base, then spin the az zero
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    tilt_x = ((1, 0, 0), (0, c, -s), (0, s, c))
    true_R = mat_mul(rot_z(-az_offset),
                     mat_mul(rot_z(tilt_axis), mat_mul(tilt_x, rot_z(-tilt_axis))))

    def reading(sky_alt, sky_az, alt_index, noise=0.0):
        m_alt, m_az = angles(mat_vec(true_R, vec(sky_alt, sky_az)))
        return (m_alt - alt_index + random.gauss(0, noise),
                m_az + random.gauss(0, noise))

    stars = {"Vega": (62.0, 290.0), "Arcturus": (25.0, 255.0), "Altair": (55.0, 170.0)}

    cases = [(0.0, -2.5), (0.05, -2.5), (0.05, 47.0)]
    for noise, alt_index in cases:
        a = Alignment()
        for name in ("Vega", "Altair"):
            a.add(name, *stars[name], *reading(*stars[name], alt_index, noise))
        want = reading(*stars["Arcturus"], alt_index)
        got = a.to_mount(*stars["Arcturus"])
        err = separation(vec(*want), vec(*got))
        print(f"noise {noise:.2f} deg, laser started {alt_index:+.1f} deg: {a.report}")
        print(f"   Arcturus pointing error {err:.4f} deg "
              f"({'PASS' if err < 0.5 else 'FAIL'}, target 0.5)")
    print(f"truth: base off level {tilt:.2f} deg, alt zero off by the 'laser started' value")


if __name__ == "__main__":
    _self_test()
