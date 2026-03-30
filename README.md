# 🌱 Smart IoT Greenhouse Controller

[cite_start]This repository contains the code for my "IoT Essentials" Individual Project[cite: 1, 2]. It is a fully functional, automated greenhouse control system built on a Raspberry Pi. 

[cite_start]The system reads environmental data using I2C sensors, visualizes it on a local OLED display and a cloud dashboard, and automatically closes the loop by controlling heating, cooling, and lighting to meet user-defined targets[cite: 6, 9].

## ✨ Features

* [cite_start]**Environmental Monitoring**: Measures real-time temperature (BMP280) and illuminance/lux (BH1750) via I2C[cite: 6].
* [cite_start]**Local UI & Display**: Physical pushbuttons allow the user to toggle modes and set target goals for both temperature and lux[cite: 7]. Live data and goals are displayed on an SSD1306 OLED screen.
* [cite_start]**Automated Climate Control**: Uses a relay module to control a heating resistor and a PC cooling fan based on the target temperature[cite: 8, 16].
* [cite_start]**Proportional Lighting Control**: Automatically dims or brightens PWM grow LEDs based on the deficit between the target lux and current ambient lux[cite: 8, 15].
* **Visual Status Indicators**: A WS2812 NeoPixel LED provides immediate visual feedback of the climate status (Red = Heating, Blue = Cooling, Green = Optimal).
* [cite_start]**Cloud Dashboard**: Telemetry data (current values, target goals, LED percentage, and system status) is streamed to an InfluxDB/Grafana dashboard for real-time monitoring[cite: 6, 13].

## 🛠 Hardware Requirements

* Raspberry Pi (with internet connection)
* [cite_start]**Sensors**: BMP280 (Temperature) & BH1750 (Light) [cite: 6]
* **Display**: SSD1306 OLED (SPI)
* **Actuators**:
    * 4-Channel Relay Module (K1 = Heater, K2 = 12V/5V PC Fan)
    * 2x LEDs (Grow lights, connected to PWM pins)
    * 1x WS2812 NeoPixel LED (Status indicator)
* [cite_start]**Inputs**: 3x Pushbuttons (Up, Down, Mode) with 100kΩ physical pull-down resistors [cite: 7]

## 🚀 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME
