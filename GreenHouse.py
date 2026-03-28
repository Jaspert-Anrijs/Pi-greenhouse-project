import time
import board
import busio
import digitalio
import neopixel
import adafruit_bmp280
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button, PWMLED, DigitalOutputDevice

# ==========================================
# 0. INFLUXDB INSTELLINGEN (Voor Grafana)
# ==========================================
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = "http://localhost:8086" 
INFLUX_TOKEN = "JOUW_INFLUXDB_TOKEN_HIER"
INFLUX_ORG = "jouw-org"
INFLUX_BUCKET = "greenhouse"

client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ==========================================
# 1. HARDWARE INSTELLINGEN
# ==========================================
i2c = busio.I2C(board.SCL, board.SDA)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)

spi = busio.SPI(board.SCK, MOSI=board.MOSI)
dc_pin = digitalio.DigitalInOut(board.D22)
reset_pin = digitalio.DigitalInOut(board.D25)
cs_pin = digitalio.DigitalInOut(board.D4) 
oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, dc_pin, reset_pin, cs_pin)

image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

heater = DigitalOutputDevice(27, active_high=False) 
cooler = DigitalOutputDevice(26, active_high=False) 

led1 = PWMLED(17) 
led2 = PWMLED(16) 
status_led = neopixel.NeoPixel(board.D18, 1, brightness=0.5) 

btn_up = Button(23, pull_up=False)
btn_mode = Button(12, pull_up=False)
btn_down = Button(24, pull_up=False)

# ==========================================
# 2. VARIABELEN EN FUNCTIES (KNOPPEN)
# ==========================================
current_mode = "TEMP"
target_temp = 20.0
target_lux = 500
heater_status = 0 

def toggle_mode():
    global current_mode
    if current_mode == "TEMP":
        current_mode = "LUX"
    else:
        current_mode = "TEMP"
    print(f"\n---> MODUS GEWIJZIGD NAAR: {current_mode} <---")

def value_up():
    global target_temp, target_lux
    if current_mode == "TEMP":
        target_temp += 0.5
        print(f"+++ Doel Temperatuur: {target_temp}°C")
    elif current_mode == "LUX":
        target_lux += 50
        print(f"+++ Doel Licht: {target_lux} lx")

def value_down():
    global target_temp, target_lux
    if current_mode == "TEMP":
        target_temp -= 0.5
        print(f"--- Doel Temperatuur: {target_temp}°C")
    elif current_mode == "LUX":
        target_lux -= 50
        print(f"--- Doel Licht: {target_lux} lx")

btn_mode.when_pressed = toggle_mode
btn_up.when_pressed = value_up
btn_down.when_pressed = value_down

# ==========================================
# 3. HOOFDPROGRAMMA (DE LOOP)
# ==========================================
print("================================================")
print("🌱 Slimme Broeikas Opgestart!")
print("Druk op CTRL+C om veilig af te sluiten.")
print("================================================\n")

try:
    while True:
        # A. Sensoren Uitlezen
        current_temp = bmp280.temperature
        current_lux = 400 # Testwaarde, pas aan naar je eigen sensor
        status_text = "OPTIMAAL"

        # B. Klimaat Controle
        if current_temp < target_temp:
            heater.on()
            cooler.off()
            status_led.fill((255, 0, 0)) 
            heater_status = 1
            status_text = "VERWARMEN"
        elif current_temp > target_temp + 0.5:
            heater.off()
            cooler.on()
            status_led.fill((0, 0, 255)) 
            heater_status = -1
            status_text = "KOELEN"
        else:
            heater.off()
            cooler.off()
            status_led.fill((0, 255, 0)) 
            heater_status = 0
            status_text =