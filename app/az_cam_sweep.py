from app.mount import Mount

STEPS_PER_DEG = 200 * 16 * 4 / 360
AZ = 2
INC = 5
SPAN = int(120 * STEPS_PER_DEG)


def az_on(m):
    return m.send("E").split()[4] == "1"


def sweep(m, direction):
    edges = []
    last = az_on(m)
    for _ in range(SPAN // INC):
        m.move(AZ, direction * INC)
        m.wait()
        now = az_on(m)
        if now != last:
            pos = m.status()[0][AZ - 1]
            edges.append(("TRIP" if now else "RELEASE", pos))
            last = now
    return edges


if __name__ == "__main__":
    m = Mount()
    m.send("V 2000")
    try:
        for label, d in (("forward", 1), ("reverse", -1)):
            print(label)
            for kind, pos in sweep(m, d):
                print(f"  {kind:8} {pos:7d} steps  {pos / STEPS_PER_DEG:8.2f} deg")
    finally:
        m.stop()
        m.close()
