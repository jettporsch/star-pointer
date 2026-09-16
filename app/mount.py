import time
import serial


class Mount:
    def __init__(self, port="/dev/cu.usbmodem103", baud=115200):
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(0.5)
        # a bare Enter clears any leftover junk in the firmware's line buffer
        self.ser.write(b"\r")
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def send(self, cmd, timeout=2.0):
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\r").encode())
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.ser.readline().decode(errors="replace").strip()
            if line == "" or line == cmd:
                continue  # skip blank lines and the echo
            if line.startswith("ERR"):
                raise RuntimeError(line)
            return line
        raise TimeoutError(f"no reply to {cmd!r}")

    def move(self, axis, steps):
        self.send(f"M {axis} {steps}")

    def status(self):
        parts = self.send("S").split()
        # POS a1 a2 BUSY b1 b2
        pos = (int(parts[1]), int(parts[2]))
        busy = (parts[4] == "1", parts[5] == "1")
        return pos, busy

    def stop(self):
        self.send("X")

    def wait(self, poll=0.05):
        while any(self.status()[1]):
            time.sleep(poll)

    def close(self):
        self.ser.close()
