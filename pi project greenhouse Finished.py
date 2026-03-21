import time
import board
from gpiozero import PWMLED, Button, DigitalOutputDevice
import adafruit_bmp280
import adafruit_bh1750
import paho.mqtt.client as mqtt

# --- 1. ThingSpeak MQTT Credentials ---
# PASTE YOUR DETAILS FROM THINGSPEAK HERE:
MQTT_BROKER = "mqtt3.thingspeak.com"
CHANNEL_ID = "3306069"       # Just the numbers, e.g., "1234567"
MQTT_CLIENT_ID = "BhcSAS0xLCI5MBIqFy08NAA"    # From the MQTT popup
MQTT_USERNAME = "BhcSAS0xLCI5MBIqFy08NAA"      # From the MQTT popup
MQTT_PASSWORD = "OTD/og5K+OpZstVtxUYV/qy5"      # From the MQTT popup

# --- 2. Hardware Setup ---
i2c = board.I2C()
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bh1750 = adafruit_bh1750.BH1750(i2c)

light_output = PWMLED(17)             
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

# --- 4. Connect to MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Successfully connected to ThingSpeak MQTT!")
    else:
        print(f"Failed to connect. Error code: {rc}")

print("Connecting to cloud...")
# Handle newer versions of paho-mqtt gracefully
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
except AttributeError:
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)

client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect

client.connect(MQTT_BROKER, 1883, 60)
client.loop_start() # This runs the network traffic in the background

print("Assignment Control Loop Started! Press CTRL+C to stop.")

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

        if current_lux < target_lux:
            brightness = (target_lux - current_lux) / 300.0 
            light_output.value = min(1.0, max(0.0, brightness))
        else:
            light_output.value = 0.0

        print(f"Actual: {current_temp:.1f}C, {current_lux:.1f} Lux | Target: {target_temp}C, {target_lux} Lux")

        # C. Send to ThingSpeak
        # The payload format MUST be field1=...&field2=...
        payload = f"field1={current_temp:.2f}&field2={current_lux:.2f}&field3={target_temp}&field4={target_lux}"
        topic = f"channels/{CHANNEL_ID}/publish/{MQTT_USERNAME}"
        
        client.publish(topic, payload)
        print("--> Data sent to ThingSpeak!")

        # Wait 16 seconds to respect ThingSpeak's rate limit!
        time.sleep(16) 

except KeyboardInterrupt:
    light_output.off()
    heater_output.off()
    client.loop_stop()
    print("\nSystem shut down safely.")