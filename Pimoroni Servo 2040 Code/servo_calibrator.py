
import time
from servo import ServoCluster, servo2040


# ============================================================
# Configuration
# ============================================================

NUM_SERVOS = 18

PIO = 0
STATE_MACHINE = 0

START_PULSE_US = 1500

# Software safety limits for calibration.
SAFE_MIN_US = 600
SAFE_MAX_US = 2400

DEFAULT_STEP_US = 10


# ============================================================
# Create the ServoCluster
# ============================================================

pins = list(range(
    servo2040.SERVO_1,
    servo2040.SERVO_18 + 1
))

servos = ServoCluster(PIO, STATE_MACHINE, pins, freq = 60)

# Each entry stores:
# [current pulse, minimum, middle, maximum]
records = [
    [START_PULSE_US, None, None, None]
    for _ in range(NUM_SERVOS)
]

selected = None
step_us = DEFAULT_STEP_US


# ============================================================
# Helper functions
# ============================================================

def select_servo(number):
    global selected

    if number < 1 or number > NUM_SERVOS:
        print("Servo number must be 1-18")
        return

    if selected is not None:
        servos.disable(selected)

    selected = number - 1

    pulse_us = records[selected][0]
    servos.pulse(selected, pulse_us)
    servos.enable(selected)

    print(
        "Selected servo {}: {} us".format(
            number, pulse_us
        )
    )


def set_pulse(pulse_us):
    if selected is None:
        print("Select a servo first: s 1")
        return

    if pulse_us < SAFE_MIN_US or pulse_us > SAFE_MAX_US:
        print(
            "Rejected. Allowed range: {}-{} us".format(
                SAFE_MIN_US, SAFE_MAX_US
            )
        )
        return

    records[selected][0] = pulse_us
    servos.pulse(selected, pulse_us)

    print(
        "Servo {}: {} us".format(
            selected + 1, pulse_us
        )
    )


def record_point(point):
    if selected is None:
        print("Select a servo first: s 1")
        return

    pulse_us = records[selected][0]

    if point == 1:
        records[selected][1] = pulse_us
        name = "MINIMUM"

    elif point == 2:
        records[selected][2] = pulse_us
        name = "MIDDLE"

    elif point == 3:
        records[selected][3] = pulse_us
        name = "MAXIMUM"

    print(
        "Recorded servo {} {}: {} us".format(
            selected + 1, name, pulse_us
        )
    )


def show_servo(number):
    r = records[number - 1]

    print(
        "Servo {:2d}: current={:4d} us, "
        "min={}, mid={}, max={}".format(
            number, r[0], r[1], r[2], r[3]
        )
    )


def show_all():
    for number in range(1, NUM_SERVOS + 1):
        show_servo(number)


def print_calibration_table():
    print()
    print("SERVO_CALIBRATION = [")

    for number, r in enumerate(records, 1):
        minimum = r[1]
        middle = r[2]
        maximum = r[3]

        print(
            "\t({}, {}, {}),  # Servo {}".format(
                minimum, middle, maximum, number
            )
        )

    print("]")
    print()


def show_help():
    print()
    print("Commands:")
    print("  s N       Select servo 1-18")
    print("  p N       Set pulse width to N microseconds")
    print("  +         Increase pulse by current step")
    print("  -         Decrease pulse by current step")
    print("  step N    Change step size in microseconds")
    print("  min       Record current pulse as minimum")
    print("  mid       Record current pulse as middle")
    print("  max       Record current pulse as maximum")
    print("  show      Show selected servo calibration")
    print("  list      Show all servo calibrations")
    print("  table     Print Python calibration table")
    print("  help      Show this help")
    print("  q         Quit")
    print()


# ============================================================
# Calibration session
# ============================================================

servos.disable_all()

print()
print("Servo 2040 - 18 channel calibration")
print("All servos initially disabled.")
print("Enter 'help' to see available commands.")
print("Select a servo with: s 1")
print()

try:
    while True:
        try:
            command = input("cal> ").strip().lower()

            if not command:
                continue

            parts = command.split()
            cmd = parts[0]

            if cmd == "q":
                break

            elif cmd == "help":
                show_help()

            elif cmd == "s" and len(parts) == 2:
                select_servo(int(parts[1]))

            elif cmd == "p" and len(parts) == 2:
                set_pulse(int(parts[1]))

            elif cmd == "+":
                if selected is not None:
                    set_pulse(
                        records[selected][0] + step_us
                    )
                else:
                    print("Select a servo first.")

            elif cmd == "-":
                if selected is not None:
                    set_pulse(
                        records[selected][0] - step_us
                    )
                else:
                    print("Select a servo first.")

            elif cmd == "step" and len(parts) == 2:
                new_step = int(parts[1])

                if new_step < 1 or new_step > 100:
                    print("Step must be between 1 and 100.")
                else:
                    step_us = new_step
                    print(
                        "Step set to {} us".format(step_us)
                    )

            elif cmd == "min":
                record_point(1)

            elif cmd == "mid":
                record_point(2)

            elif cmd == "max":
                record_point(3)

            elif cmd == "show":
                if selected is None:
                    print("Select a servo first.")
                else:
                    show_servo(selected + 1)

            elif cmd == "list":
                show_all()

            elif cmd == "table":
                print_calibration_table()

            else:
                print("Unknown command. Enter 'help'.")

        except ValueError:
            print("Invalid number. Check the command syntax.")

finally:
    servos.disable_all()
    print("All servo outputs disabled.")
    print_calibration_table()
    print("Calibration session ended.")

