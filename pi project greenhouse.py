import time
import board
from gpiozero import LED
import adafruit_bmp280
import adafruit_bh1750

# --- 1. Set up the Sensors ---
# Create the I2C connection (automatically uses physical pins 3 and 5)
i2c = board.I2C()

# Link the sensors to the I2C connection
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bh1750 = adafruit_bh1750.BH1750(i2c)

# --- 2. Set up the LEDs ---
# Using the specific GPIO pins you chose!
led1 = LED(17)
led2 = LED(18)

print("Sensors and LEDs are running! Press CTRL+C to stop.")

try:
    # The 'while True' loop keeps the program running continuously
    while True:
        
        # Read data from the sensors
        temperature = bmp280.temperature
        pressure = bmp280.pressure
        light_level = bh1750.lux

        # Print the values nicely to the screen
        # The ':.1f' rounds the numbers to 1 decimal place
        print(f"Temp: {temperature:.1f} °C | Pressure: {pressure:.1f} hPa | Light: {light_level:.1f} Lux")

        # Blink the first LED
        led1.on()
        time.sleep(0.3)
        led1.off()
        
        # Blink the second LED
        led2.on()
        time.sleep(0.3)
        led2.off()

        # Wait for 1 second before reading the sensors again
        time.sleep(1)

except KeyboardInterrupt:
    # If you stop the script (with CTRL+C), this safely turns off the LEDs
    led1.off()
    led2.off()
    print("\nProgram closed safely. Lights out!")