# v0.14
#19 Oct 26


import time
import gc
from machine import I2CTarget, Pin
from servo import ServoCluster, servo2040
from pimoroni import Button # user button on board
from plasma import WS2812 # leds on board


# ============================================================
# Configuration
# ============================================================

# Create the user button
user_sw = Button(servo2040.USER_SW)

# Setup LED bar
led_bar = WS2812(servo2040.NUM_LEDS, 1, 0, servo2040.LED_DATA) # Uses PIO 1 and State Machine 0
BRIGHTNESS = 0.4      # The brightness of the LEDs
UPDATES = 50          # How many times to update LEDs and Servos per second
MAX_CURRENT = 3.0     # The maximum current, in amps, to show on the meter

# I2C config
I2C_ADDRESS = 0x42
I2C_ID = 0
I2C_SDA = Pin(servo2040.SDA)
I2C_SCL = Pin(servo2040.SCL)

# Servo config
gc.collect() # Free up hardware resources ahead of creating a new ServoCluster
NUM_SERVOS = 18
PIO = 0 # ServoCluster uses PIO to drive all 18 outputs.
STATE_MACHINE = 0
FREQUENCY = 60

servo_pins = list(
    range(
        servo2040.SERVO_1,
        servo2040.SERVO_18 + 1
    )
)

servos = ServoCluster(
    PIO,
    STATE_MACHINE,
    servo_pins,
    freq = FREQUENCY
)
#servos.frequency(FREQUENCY)


# Servo calibrations (in microseconds)
#                1     2     3     4     5     6     7     8     9     10    11    12    13    14    15    16    17    18                    
servo_min =    [610,  610,  373,  347,  365,  371, 394, 355, 375, 384, 360, 401, 378, 375, 351, 389, 397, 391] # -90
servo_mid =    [1460, 1460, 373,  347,  365,  371, 394, 355, 375, 384, 360, 401, 378, 375, 351, 389, 397, 391] # 0
servo_max =    [2360, 2360, 373,  347,  365,  371, 394, 355, 375, 384, 360, 401, 378, 375, 351, 389, 397, 391] # +90

# apply the calibration values to all the servos in the cluster 
for i in range(NUM_SERVOS):
    cal = servos.calibration(i) # first get a copy of existing calibration
    cal.apply_three_pairs(servo_min[i], servo_mid[i], servo_max[i], -90, 0, 90) # modify calibration
    servos.calibration(i, cal) # apply to servo




# Register addresses
REG_SERVO_START = 0x00
REG_SERVO_END = 0x11

REG_ENABLE_MASK = 0x20

REG_STATUS = 0x30
REG_VERSION = 0x31

PROTOCOL_VERSION = 1
STATUS_OK = 0x00


# ============================================================
# I2C register memory
# ============================================================

# 64 bytes gives us plenty of room for future registers.
registers = bytearray(64)

# Initial servo positions.
# 90 = 0 degrees.
for i in range(NUM_SERVOS):
    registers[REG_SERVO_START + i] = 90

# All 18 servos enabled.
registers[REG_ENABLE_MASK + 0] = 0xFF
registers[REG_ENABLE_MASK + 1] = 0xFF
registers[REG_ENABLE_MASK + 2] = 0x03

registers[REG_STATUS] = STATUS_OK
registers[REG_VERSION] = PROTOCOL_VERSION


# ============================================================
# State mirrored from the I2C registers
# ============================================================

servo_values = [90] * NUM_SERVOS

enable_mask = 0x3FFFF


# ============================================================
# Helper functions
# ============================================================

def get_enable_mask():
    return (
        registers[REG_ENABLE_MASK + 0]
        | (registers[REG_ENABLE_MASK + 1] << 8)
        | (registers[REG_ENABLE_MASK + 2] << 16)
    )


def set_servo_value(index, encoded_value):
    """
    Convert the I2C representation:

    0   -> -90 degrees
    90  ->   0 degrees
    180 -> +90 degrees
    """

    if encoded_value > 180:
        encoded_value = 180

    angle = encoded_value - 90

    if angle != servo_values[index]:
        servo_values[index] = angle
        servos.value(index, angle)


def update_enable_state(new_mask):
    global enable_mask

    changed = new_mask ^ enable_mask

    if changed == 0:
        return

    for i in range(NUM_SERVOS):
        bit = 1 << i

        if changed & bit:
            if new_mask & bit:
                servos.enable(i)
            else:
                servos.disable(i)

    enable_mask = new_mask


def process_registers():
    """
    Check for changes made by the I2C controller.

    No I2C interrupt handler is required here. I2CTarget updates
    the register memory directly, and this loop processes the
    changes in normal Python context.
    """

    # Process servo positions.
    for i in range(NUM_SERVOS):
        encoded_value = registers[REG_SERVO_START + i]

        if encoded_value != servo_values[i] + 90:
            set_servo_value(i, encoded_value)

    # Process enable mask.
    new_mask = get_enable_mask()

    if new_mask != enable_mask:
        update_enable_state(new_mask)


def initialise_servos():
    """
    Set every servo to its initial register position and enable
    the servos according to the initial enable mask.
    """

    for i in range(NUM_SERVOS):
        angle = registers[REG_SERVO_START + i] - 90

        if angle < -90:
            angle = -90

        if angle > 90:
            angle = 90

        servo_values[i] = angle
        servos.value(i, angle, load=False)

    # Load all servo changes together.
    servos.load()

    update_enable_state(get_enable_mask())


# ============================================================
# Pre-Loop
# ============================================================

# Start I2C target
i2c_target = I2CTarget(
    I2C_ID,
    addr = I2C_ADDRESS,
    mem = registers,
    mem_addrsize = 8,
    scl = I2C_SCL,
    sda = I2C_SDA
)

led_bar.start() # Start updating the LED bar
initialise_servos()

counter = 0
light = 0

print("Servo 2040 I2C target started")
print("I2C address: 0x{:02X}".format(I2C_ADDRESS))
print("Servos: {}".format(NUM_SERVOS))
print("Protocol version: {}".format(PROTOCOL_VERSION))


# ============================================================
# Main loop
# ============================================================

while not user_sw.raw(): # Loop until user button is pressed
    process_registers()

    
    counter+=1
    if counter >= 100:
        if light == 0:
            led_bar.set_hsv(0, 0.4, 0.3, BRIGHTNESS)
            light = 1
        else:
            led_bar.set_hsv(0, 0.8, 0.6, BRIGHTNESS)
            light = 0
        counter = 0
    
    time.sleep_ms(2)
    


# ============================================================
# Post loop
# ============================================================
    
servos.disable_all() # Disable the servos
led_bar.clear() # Turn off the LED bar

print("Program terminated")

