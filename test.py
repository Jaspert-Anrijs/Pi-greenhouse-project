import time
import board
from gpiozero import PWMLED, Button, DigitalOutputDevice
import adafruit_bmp280
import adafruit_bh1750
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

# --- 1. InfluxDB Setup ---
# PASTE YOUR INFLUXDB DETAILS HERE:
URL = "https://us-east-1-1.aws.cloud2.influxdata.com" # Replace with your exact URL
TOKEN = "JH5pxxMV3zYwNuu3YeUhomf29b3GVMXnQGPkRpIbQkbJFjRE3aB-djrKsjc3y6H7aZ_zC9i4fjqMz34xIGsadQ=="
ORG = "3acd0f7e84aa93fD"
BUCKET = "greenhouse"

# Connect to the database
client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# --- 2. Hardware Setup ---
i2c = board.I2C()
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bh1750 = adafruit_bh1750.BH1750(i2c)
# Set up BOTH LEDs for dimming (PWM)
led1 = PWMLED(17)             
led2 = PWMLED(18)

heater_output = DigitalOutputDevice(27)           

btn_up = Button(23, pull_up=True)
btn_down = Button(24, pull_up=True)

# --- 3. Targets & Functions ---
target_temp = 25.0
target_lux = 200.0

def increase_targets():
    global target_temp, target_lux
    target_temp += 1.0; target_lux += 50.0
    print(f"\n[SETTINGS] Target Temp: {target_temp}C | Target Lux: {target_lux}")

def decrease_targets():
    global target_temp, target_lux
    target_temp -= 1.0; target_lux -= 50.0
    print(f"\n[SETTINGS] Target Temp: {target_temp}C | Target Lux: {target_lux}")

btn_up.when_pressed = increase_targets
btn_down.when_pressed = decrease_targets

print("InfluxDB Control Loop Started! Press CTRL+C to stop.")

try:
    while True:
        # A. Read Sensors
        current_temp = bmp280.temperature
        current_lux = bh1750.lux

        # B. Control Loop
        if current_temp < target_temp:
            heater_output.on()
            heater_status = 1
        else:
            heater_output.off()
            heater_status = 0

        # 2. Synchronized Light Control (Inverse Proportional)
        if current_lux < target_lux:
            # Calculate how far away we are from the target.
            # If target is 200 and actual is 0, brightness = 1.0 (100%)
            # If target is 200 and actual is 100, brightness = 0.5 (50%)
            brightness = (target_lux - current_lux) / target_lux
            
            # Ensure the value strictly stays between 0.0 and 1.0
            safe_brightness = min(1.0, max(0.0, brightness))
            
            # Apply the exact same brightness to both LEDs
            led1.value = safe_brightness
            led2.value = safe_brightness
            
            # Save this value to send to InfluxDB
            current_brightness = safe_brightness
        else:
            # It is bright enough, turn both LEDs completely off
            led1.value = 0.0
            led2.value = 0.0
            current_brightness = 0.0

        print(f"Actual: {current_temp:.1f}C, {current_lux:.1f} Lux | Target: {target_temp}C, {target_lux} Lux")

        # C. Send to InfluxDB
        # We package our data into a "Point"
        point = influxdb_client.Point("measurements") \
            .field("actual_temp", current_temp) \
            .field("actual_lux", current_lux) \
            .field("target_temp", target_temp) \
            .field("target_lux", target_lux) \
            .field("heater_status", heater_status) \
            .field("led_brightness", current_brightness)

        # Write to the cloud
        write_api.write(bucket=BUCKET, org=ORG, record=point)
        print("--> Data saved to InfluxDB")

        # Wait 5 seconds before the next loop
        time.sleep(5) 

except KeyboardInterrupt:
    light_output.off()
    heater_output.off()
    client.close()
    print("\nSystem shut down safely.")