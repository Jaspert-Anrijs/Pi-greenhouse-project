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

# Vul hier jouw eigen InfluxDB gegevens in:
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com" # Of het IP-adres van je InfluxDB server
INFLUX_TOKEN = "JH5pxxMV3zYwNuu3YeUhomf29b3GVMXnQGPkRpIbQkbJFjRE3aB-djrKsjc3y6H7aZ_zC9i4fjqMz34xIGsadQ=="
INFLUX_ORG = "3acd0f7e84aa93fD"
INFLUX_BUCKET = "greenhouse"

# Maak de InfluxDB client aan
client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ==========================================
# 1. HARDWARE INSTELLINGEN
# ==========================================

# I2C Bus voor sensoren (Temperatuur en Licht)
i2c = busio.I2C(board.SCL, board.SDA)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)

# SPI Bus voor het OLED Scherm
spi = busio.SPI(board.SCK, MOSI=board.MOSI)
dc_pin = digitalio.DigitalInOut(board.D22)
reset_pin = digitalio.DigitalInOut(board.D25)
cs_pin = digitalio.DigitalInOut(board.D4) # D4 als veilige spook-pin
oled = adafruit_ssd1306.SSD1306_SPI(128, 64, spi, dc_pin, reset_pin, cs_pin)

# Canvas voor het OLED scherm voorbereiden
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

# Relais (Active Low voor de 4-kanaals module)
heater = DigitalOutputDevice(27, active_high=False) # K1: Verwarming
cooler = DigitalOutputDevice(26, active_high=False) # K2: PC Fan / Koeling

# LEDs
led1 = PWMLED(17) # Groeilamp 1
led2 = PWMLED(16) # Groeilamp 2
status_led = neopixel.NeoPixel(board.D18, 1, brightness=0.5) # De slimme RGB LED

# Knoppen (met externe 100k pull-down weerstanden)
btn_up = Button(23, pull_up=False)
btn_mode = Button(12, pull_up=False)
btn_down = Button(24, pull_up=False)

# ==========================================
# 2. VARIABELEN EN FUNCTIES (KNOPPEN)
# ==========================================

current_mode = "TEMP"
target_temp = 20.0
target_lux = 500
heater_status = 0 # 1 = Verwarmen, -1 = Koelen, 0 = OK

def toggle_mode():
    global current_mode
    if current_mode == "TEMP":
        current_mode = "LUX"
    else:
        current_mode = "TEMP"
    print(f"Modus gewijzigd naar: {current_mode}")

def value_up():
    global target_temp, target_lux
    if current_mode == "TEMP":
        target_temp += 0.5
    elif current_mode == "LUX":
        target_lux += 50

def value_down():
    global target_temp, target_lux
    if current_mode == "TEMP":
        target_temp -= 0.5
    elif current_mode == "LUX":
        target_lux -= 50

# Koppel knoppen aan de functies
btn_mode.when_pressed = toggle_mode
btn_up.when_pressed = value_up
btn_down.when_pressed = value_down

# ==========================================
# 3. HOOFDPROGRAMMA (DE LOOP)
# ==========================================

print("Slimme Broeikas opgestart! Druk op CTRL+C om te stoppen.")

try:
    while True:
        # A. Sensoren Uitlezen
        current_temp = bmp280.temperature
        
        # Testwaarde voor lux (Vervang dit door je eigen lux-sensor code!)
        current_lux = 400 

        # B. Klimaat Controle (Verwarmen / Koelen)
        if current_temp < target_temp:
            heater.on()
            cooler.off()
            status_led.fill((255, 0, 0)) # Rood
            heater_status = 1
        elif current_temp > target_temp + 0.5:
            heater.off()
            cooler.on()
            status_led.fill((0, 0, 255)) # Blauw
            heater_status = -1
        else:
            heater.off()
            cooler.off()
            status_led.fill((0, 255, 0)) # Groen
            heater_status = 0

        # C. Licht Controle (Dimmen & Percentage berekenen)
        if current_lux < target_lux:
            led1.value = 1.0 # 100% aan
            led2.value = 1.0
        else:
            led1.value = 0.0 # 0% (Uit)
            led2.value = 0.0
            
        # Bereken het exacte percentage van de LED (0 tot 100)
        led_percentage = int(led1.value * 100)

        # D. OLED Scherm Updaten
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0) # Scherm leegmaken
        draw.text((0, 0), "GREENHOUSE DASHBOARD", font=font, fill=255)
        
        # Actieve modus en doelen
        if current_mode == "TEMP":
            draw.text((0, 14), f"> Temp: {current_temp:.1f}C (Doel: {target_temp})", font=font, fill=255)
            draw.text((0, 26), f"  Licht: {current_lux:.0f}lx (Doel: {target_lux})", font=font, fill=255)
        else:
            draw.text((0, 14), f"  Temp: {current_temp:.1f}C (Doel: {target_temp})", font=font, fill=255)
            draw.text((0, 26), f"> Licht: {current_lux:.0f}lx (Doel: {target_lux})", font=font, fill=255)
        
        # --- NIEUW: Visuele LED Balk op OLED ---
        draw.text((0, 40), f"LED:{led_percentage}%", font=font, fill=255)
        # Teken de buitenrand van de balk
        draw.rectangle((45, 40, 128, 50), outline=255, fill=0)
        # Vul de balk op basis van het percentage
        vul_breedte = int((led_percentage / 100.0) * (128 - 45))
        if vul_breedte > 0:
            draw.rectangle((45, 40, 45 + vul_breedte, 50), outline=255, fill=255)
        
        # Status waarschuwing onderaan
        if heater_status == 1:
            draw.rectangle((0, 52, 128, 64), fill=255) # Witte balk
            draw.text((5, 54), "STATUS: VERWARMEN", font=font, fill=0) # Zwarte tekst
        elif heater_status == -1:
            draw.text((5, 54), "STATUS: KOELEN", font=font, fill=255)
        else:
            draw.text((5, 54), "STATUS: OPTIMAAL", font=font, fill=255)
        
        oled.image(image)
        oled.show()

        # E. Data naar InfluxDB sturen
        try:
            point = influxdb_client.Point("klimaat") \
                .field("temperatuur", float(current_temp)) \
                .field("lux", float(current_lux)) \
                .field("doel_temp", float(target_temp)) \
                .field("doel_lux", float(target_lux)) \
                .field("led_percentage", float(led_percentage)) \
                .field("heater_status", int(heater_status))
            
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        except Exception as e:
            # Als InfluxDB niet bereikbaar is, print de error maar laat het project doordraaien
            print(f"InfluxDB fout: {e}")

        # Wacht 1 seconde en begin opnieuw
        time.sleep(1)

# ==========================================
# 4. VEILIG AFSLUITEN (CTRL+C)
# ==========================================
except KeyboardInterrupt:
    print("\nProgramma gestopt. Alles wordt veilig uitgeschakeld...")
    heater.off()
    cooler.off()
    led1.off()
    led2.off()
    status_led.fill((0, 0, 0))
    oled.fill(0)
    oled.show()
    print("Klaar! Succes met je presentatie!")