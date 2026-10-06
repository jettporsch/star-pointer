from app.mount import Mount

STEPS_PER_DEG = 200 * 16 * 4 / 360
AZ = 2
INC = 5
LIMIT = int(170 * STEPS_PER_DEG)   # max search each way
PAST = int(10 * STEPS_PER_DEG)     # overshoot past release before coming back


def az_on(m):
    return m.send("E").split()[4] == "1"


def pos(m):
    return m.status()[0][AZ - 1]


def step(m, n):
    m.move(AZ, n)
    m.wait()


def go_to(m, target):
    while pos(m) != target:
        d = target - pos(m)
        step(m, max(-500, min(500, d)))


def map_side(m, start, direction):
    release = None
    while abs(pos(m) - start) < LIMIT:
        step(m, direction * INC)
        if not az_on(m):
            release = pos(m)
            break
    if release is None:
        return None, None
    step(m, direction * PAST)
    trip = None
    for _ in range(2 * PAST // INC):
        step(m, -direction * INC)
        if az_on(m):
            trip = pos(m)
            break
    return release, trip


def deg(steps):
    return f"{steps / STEPS_PER_DEG:+.2f} deg"


if __name__ == "__main__":
    m = Mount()
    m.send("V 2000")
    try:
        if not az_on(m):
            print("switch isn't pressed at the start, put the top of the cam on the lever")
        else:
            start = pos(m)
            rel = {}
            for name, d in (("CCW", -1), ("CW", 1)):
                print(f"mapping {name}...")
                r, t = map_side(m, start, d)
                go_to(m, start)
                rel[name] = r
                if r is None:
                    print(f"  {name}: no release within 170 deg")
                elif t is None:
                    print(f"  {name}: releases at {deg(r - start)}, never tripped coming back")
                else:
                    print(f"  {name}: releases at {deg(r - start)}, trips back at {deg(t - start)}, gap {abs(r - t) / STEPS_PER_DEG:.2f} deg")
            if rel["CCW"] is not None and rel["CW"] is not None:
                print(f"switch is on for about {(rel['CW'] - rel['CCW']) / STEPS_PER_DEG:.1f} deg")
    finally:
        m.stop()
        m.close()
