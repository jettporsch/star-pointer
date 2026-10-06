import time
from app.mount import Mount

STEPS_PER_DEG = 200 * 16 * 4 / 360
INC = 5
LIMIT = int(180 * STEPS_PER_DEG)


def read_switch(m):
    a = m.send("E").split()[4]
    b = m.send("E").split()[4]
    if a != b:
        print("    flicker")
    return b == "1"


def az_pos(m):
    return int(m.send("S").split()[2])


def move(m, n):
    r = m.send(f"M 2 {n}")
    if r.strip() != "OK":
        print("    move reply:", r)
    while m.send("S").split()[5] == "1":
        time.sleep(0.005)


def deg(steps):
    return f"{steps / STEPS_PER_DEG:+.2f} deg"


def walk(m, start, direction, changes_wanted):
    state = read_switch(m)
    found = 0
    while abs(az_pos(m) - start) < LIMIT:
        move(m, direction * INC)
        now = read_switch(m)
        if now != state:
            print(f"  {'ON ' if now else 'OFF'} at {deg(az_pos(m) - start)}")
            state = now
            found += 1
            if found == changes_wanted:
                return
    print("  hit the 180 deg limit")


if __name__ == "__main__":
    m = Mount()
    m.send("V 2000")
    try:
        start = az_pos(m)
        print("start:", "ON" if read_switch(m) else "OFF")
        print("going CCW until it changes")
        walk(m, start, -1, 1)
        print("going CW until it changes twice")
        walk(m, start, 1, 2)
        print("returning to start")
        while az_pos(m) != start:
            d = start - az_pos(m)
            move(m, max(-500, min(500, d)))
    finally:
        m.stop()
        m.close()
