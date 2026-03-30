import time
import board
import busio
import digitalio
import neopixel
import adafruit_bmp280
import adafruit_bh1750
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
from gpiozero import Button, PWMLED, DigitalOutputDevice

# ==========================================
# 0. INFLUXDB INSTELLINGEN
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
bh1750 = adafruit_bh1750.BH1750(i2c)

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
# 2. VARIABELEN EN FUNCTIES
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
        target_temp += 0.25
        print(f"+++ Doel Temperatuur: {target_temp}°C")
    elif current_mode == "LUX":
        target_lux += 25
        print(f"+++ Doel Licht: {target_lux} lx")

def value_down():
    global target_temp, target_lux
    if current_mode == "TEMP":
        target_temp -= 0.25
        print(f"--- Doel Temperatuur: {target_temp}°C")
    elif current_mode == "LUX":
        target_lux -= 25
        print(f"--- Doel Licht: {target_lux} lx")

btn_mode.when_pressed = toggle_mode
btn_up.when_pressed = value_up
btn_down.when_pressed = value_down

# ==========================================
# 3. HOOFDPROGRAMMA 
# ==========================================
print("Slimme Broeikas Opgestart!")
print("Druk op CTRL+C om veilig af te sluiten.")

try:
    while True:
        # A. Sensoren Uitlezen
        current_temp = bmp280.temperature
        current_lux = bh1750.lux
        status_text = "OPTIMAAL"

        # B. Klimaat Controle
        if current_temp < target_temp:
            heater.on()
            cooler.off()
            # Stuur (Groen, Rood, Blauw)
            status_led.fill((0, 255, 0)) 
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
            status_led.fill((255, 0, 0)) 
            heater_status = 0
            status_text = "OPTIMAAL"

       # C. Licht Controle
        if current_lux < target_lux:
            # 1. Bereken hoeveel lux we tekortkomen
            lux_verschil = target_lux - current_lux
            max_lux_verschil = 300.0 
            dim_waarde = lux_verschil / max_lux_verschil
            if dim_waarde > 1.0:
                dim_waarde = 1.0
                
            led1.value = dim_waarde
            led2.value = dim_waarde
        else:
            led1.value = 0.0
            led2.value = 0.0
            
        # Bereken het percentage voor op het scherm en InfluxDB
        led_percentage = int(led1.value * 100)
            
        led_percentage = int(led1.value * 100)

        # D. OLED Scherm Updaten
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0) 
        draw.text((0, 0), "GREENHOUSE DASHBOARD", font=font, fill=255)
        
        if current_mode == "TEMP":
            draw.text((0, 14), f"> Temp: {current_temp:.1f}C (Doel: {target_temp})", font=font, fill=255)
            draw.text((0, 26), f"  Licht: {current_lux:.0f}lx (Doel: {target_lux})", font=font, fill=255)
        else:
            draw.text((0, 14), f"  Temp: {current_temp:.1f}C (Doel: {target_temp})", font=font, fill=255)
            draw.text((0, 26), f"> Licht: {current_lux:.0f}lx (Doel: {target_lux})", font=font, fill=255)
        
        draw.text((0, 40), f"LED:{led_percentage}%", font=font, fill=255)
        draw.rectangle((45, 40, 128, 50), outline=255, fill=0)
        vul_breedte = int((led_percentage / 100.0) * (128 - 45))
        if vul_breedte > 0:
            draw.rectangle((45, 40, 45 + vul_breedte, 50), outline=255, fill=255)
        
        if heater_status == 1:
            draw.rectangle((0, 52, 128, 64), fill=255) 
            draw.text((5, 54), f"STATUS: {status_text}", font=font, fill=0) 
        else:
            draw.text((5, 54), f"STATUS: {status_text}", font=font, fill=255)
        
        oled.image(image)
        oled.show()

        # E. Terminal Output
        print(f"[Modus: {current_mode}] Temp: {current_temp:.1f}°C ({target_temp}) | Lux: {current_lux} ({target_lux}) | LED: {led_percentage}% | Klimaat: {status_text}")

        # F. Data naar InfluxDB sturen
        try:
            point = influxdb_client.Point("klimaat") \
                .field("temperatuur", float(current_temp)) \
                .field("lux", float(current_lux)) \
                .field("doel_temp", float(target_temp)) \
                .field("doel_lux", float(target_lux)) \
                .field("led_percentage", float(led_percentage)) \
                .field("heater_status", int(heater_status))
            
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        except Exception:
            pass 

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
    print("Klaar!")