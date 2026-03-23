import time
import board
import neopixel
from gpiozero import PWMLED, Button
import adafruit_bmp280
import adafruit_bh1750
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import busio
import digitalio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. INFLUXDB INSTELLINGEN
# ==========================================
URL = "https://us-east-1-1.aws.cloud2.influxdata.com" # Check of dit jouw URL is!
TOKEN = "JH5pxxMV3zYwNuu3YeUhomf29b3GVMXnQGPkRpIbQkbJFjRE3aB-djrKsjc3y6H7aZ_zC9i4fjqMz34xIGsadQ=="
ORG = "3acd0f7e84aa93fD"
BUCKET = "greenhouse"

# Verbind met InfluxDB
client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ==========================================
# 2. HARDWARE INSTELLINGEN
# ==========================================

# ==========================================
# OLED SCHERM INSTELLINGEN (SPI)
# ==========================================
spi = busio.SPI(board.SCK, MOSI=board.MOSI)
dc_pin = digitalio.DigitalInOut(board.D22)
reset_pin = digitalio.DigitalInOut(board.D25)
cs_pin = digitalio.DigitalInOut(board.D4) # Veranderd naar D4 omdat D8 bezet is door hardware SPI

# Maak het scherm aan (128x64 is de standaard resolutie)
oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, dc_pin, reset_pin, cs_pin)

# Maak een digitaal leeg "canvas" aan om tekst op te tekenen
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

# I2C Sensoren
i2c = board.I2C()
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bh1750 = adafruit_bh1750.BH1750(i2c)

# Twee gewone LEDs (voor de licht-simulatie) op GPIO 17 en 18
led1 = PWMLED(17)             
led2 = PWMLED(16)

# Slimme RGB LED (WS2812/APA106) op GPIO 21 (Data in)
# We gebruiken auto_write=False zodat we zelf bepalen wanneer hij van kleur wisselt
status_led = neopixel.NeoPixel(board.D18, 1, brightness=0.5, auto_write=False, pixel_order=neopixel.RGB)

# Knoppen op GPIO 23 en 24
btn_up = Button(23, pull_up=True)
btn_down = Button(24, pull_up=True)

# ==========================================
# 3. DOELWAARDEN & KNOPPEN LOGICA
# ==========================================
target_temp = 25.0
target_lux = 300.0

def increase_targets():
    global target_temp, target_lux
    target_temp += 1.0
    target_lux += 25
    print(f"\n[INSTELLINGEN] Doel Temp: {target_temp}C | Doel Lux: {target_lux}")

def decrease_targets():
    global target_temp, target_lux
    target_temp -= 1.0
    target_lux -= 25.0
    print(f"\n[INSTELLINGEN] Doel Temp: {target_temp}C | Doel Lux: {target_lux}")

btn_up.when_pressed = increase_targets
btn_down.when_pressed = decrease_targets

print("Systeem gestart! Druk op CTRL+C om veilig af te sluiten.")

# ==========================================
# 4. DE HOOFD-LOOP (CONTROL LOOP)
# ==========================================
try:
    while True:
        # A. Lees Sensoren
        current_temp = bmp280.temperature
        current_lux = bh1750.lux

        # B. Temperatuur Controle (De simulatie LED)
        if current_temp < target_temp:
            # Het is te koud -> Verwarmen -> ROOD
            status_led[0] = (255, 0, 0)
            status_led.show()
            heater_status = 1
        else:
            # Het is warm genoeg -> Koelen/Uit -> BLAUW
            status_led[0] = (0, 0, 255)
            status_led.show()
            heater_status = -1

        # C. Licht Controle (De twee witte LEDs dimmen synchroon)
        if current_lux < target_lux:
            # Bereken hoeveel licht er bij moet (0.0 tot 1.0)
            brightness = (target_lux - current_lux) / target_lux
            safe_brightness = min(1.0, max(0.0, brightness)) # Blijf altijd tussen 0 en 1
            
            led1.value = safe_brightness
            led2.value = safe_brightness
            current_brightness = safe_brightness
        else:
            # Te veel licht -> LEDs helemaal uit
            led1.value = 0.0
            led2.value = 0.0
            current_brightness = 0.0

        print(f"Actueel: {current_temp:.1f}C, {current_lux:.1f} Lux | Doel: {target_temp}C, {target_lux} Lux")

# E. Update het OLED Scherm
        # 1. Maak het canvas eerst helemaal leeg (zwarte rechthoek)
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        
        # 2. Schrijf de tekst (x, y coördinaten)
        draw.text((0, 0), "GREENHOUSE DASHBOARD", font=font, fill=255)
        draw.text((0, 16), f"Temp : {current_temp:.1f}C (Doel: {target_temp})", font=font, fill=255)
        draw.text((0, 32), f"Licht: {current_lux:.0f}lx (Doel: {target_lux})", font=font, fill=255)
        
        if heater_status == 1:
            draw.text((0, 48), "Status: VERWARMEN", font=font, fill=255)
        else:
            draw.text((0, 48), "Status: KOELEN/OK", font=font, fill=255)
        
        # 3. Stuur het getekende plaatje naar het fysieke scherm
        oled.image(image)
        oled.show()

        # D. Stuur Data naar InfluxDB
        point = influxdb_client.Point("measurements") \
            .field("actual_temp", current_temp) \
            .field("actual_lux", current_lux) \
            .field("target_temp", target_temp) \
            .field("target_lux", target_lux) \
            .field("heater_status", heater_status) \
            .field("led_brightness", current_brightness)

        write_api.write(bucket=BUCKET, org=ORG, record=point)
        print("--> Data verzonden naar InfluxDB")

        # Wacht 5 seconden om je database niet te overspoelen
        time.sleep(5) 

# ==========================================
# 5. VEILIG AFSLUITEN (CTRL+C)
# ==========================================
except KeyboardInterrupt:
    led1.off()
    led2.off()
    status_led.fill((0, 0, 0)) # Zet de slimme LED op zwart (uit)
    status_led.show()
    client.close()
    oled.fill(0)
    oled.show()
    print("\nSysteem is veilig afgesloten. LEDs en databaseverbinding zijn uitgeschakeld.")
    # (Zet dit bij de andere .off() en .fill() commando's)