# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cryogenic probe test stand slow control system for the nEXO experiment. Two interacting hardware layers:

1. **Arduino** (in `IO_AD7150/`) — reads the AD7150 capacitance sensor over I2C and streams CSV data over USB serial at 9600 baud.
2. **Raspberry Pi** (in `temperature-control/`) — reads temperature via SPI (MAX31856/MAX31865 ADCs), reads capacitance data from the Arduino over serial, runs PID control, and logs everything to CSV.

The `thickness_monitor/` folder contains standalone Python scripts for capacitance-only monitoring without the temperature control loop.

## Running the Scripts

### Arduino firmware
Flash `IO_AD7150/IO_AD7150.ino` via the Arduino IDE. The sketch streams `ADC,CAPDAC,InputRange,Capacitance` lines over serial at 9600 baud. The library lives in both `IO_AD7150/` (working copy) and `libraries/IO_AD7150/` (Arduino library path copy — keep in sync).

### Python control scripts (Raspberry Pi)
All scripts run directly with Python 3. No build step. The active entry points are:

```bash
# Combined temp + capacitance monitoring with PID + relay control
python3 temperature-control/monitor.py

# Temperature-only PID with analog DAC output (MCP4725)
python3 temperature-control/temperature_pid_control.py

# Standalone capacitance monitor with Tkinter GUI
python3 thickness_monitor/CapSerial_real-time-plotting.py
```

### Test mode (without hardware)
```bash
TEST_MODE=1 python3 temperature-control/temperature_control.py
```
This swaps in mock hardware modules (`mocks.py`) for `board`, `digitalio`, and `adafruit_max31856`.

### Install dependencies (thickness_monitor)
```bash
cd thickness_monitor
pip install -r requirements.txt
```

## Architecture

### Capacitance measurement
The AD7150 capacitance chip (I2C address `0x48`) is read by the Arduino. The absolute capacitance formula is:

```
capacitance = (ADC - 12288) / 40944 * inputRange + capdac * 12.5 / 64
```

The input range is set by two bits in the CH1 Setup register and maps: `0b00 → 2 pF`, `0b01 → 0.5 pF`, `0b10 → 1 pF`, `0b11 → 4 pF`. The Arduino is configured for `AD7150_RANGE_0_4` (4 pF range, 8 pF CAPDAC step).

The Arduino serial output is consumed by Python scripts that open `/dev/ttyACM0` or `/dev/ttyACM1` depending on the script.

### Temperature sensors and heater control
Two sensor generations co-exist:
- **MAX31856** (thermocouple) — used in older `temperature_control.py`. 4 sensors: ColdHead (D13), HeatExF (D16), HeatExB (D25), Chamber (D26). On/off relay heaters on D22, D23.
- **MAX31865** (RTD, PT100) — used in `monitor.py` and `temperature_pid_control.py`. 2 sensors: Tip (D19), Ceramic (D16). Single relay on D6, or analog DAC output via MCP4725 (I2C `0x62`).

### PID controller
`temperature-control/PID.py` is the ivmech/ivPID library (MIT). Usage:

```python
controller = PID.PID(P, I, D)
controller.SetPoint = target_temperature
controller.setSampleTime(1)   # seconds
controller.update(measured_temp)
mv = controller.output        # positive → heat on, negative → heat off
```

Relay scripts threshold `mv > 0` for on/off. The DAC script maps `mv` to a 12-bit value sent to MCP4725. Windup guard defaults to ±20.

Current PID tuning (Ziegler-Nichols from ultimate gain 0.2, period 60s):
```python
P = 0.2 * 0.6    # = 0.12
I = 1.2 * 0.2 / 60
D = 3 * 0.2 * 60 / 40
```
Target setpoint: **-110 °C**.

### Temperature calibration
Each script has a `calibrated_temps(raw, sensor_name)` function that applies a linear correction derived from calibration runs. Coefficients differ between the MAX31856 and MAX31865 generations and between sensors — always check which script/sensor you are working with before changing these.

### Data logging
All scripts write timestamped CSV files to a `Logs/` subdirectory next to the script. Log files rotate at 4 MB. Errors are appended to `Logs/Error Logs.txt` (or `Logs/Error Logs/errors.txt`). The `finally` block always closes the log file and turns off heaters/relay.

## Hardware Pin Summary

| Signal | Pin | Script |
|--------|-----|--------|
| ColdHead TC (MAX31856) | SPI CS D13 | temperature_control.py |
| HeatExF TC (MAX31856) | SPI CS D16 | temperature_control.py |
| HeatExB TC (MAX31856) | SPI CS D25 | temperature_control.py |
| Chamber TC (MAX31856) | SPI CS D26 | temperature_control.py |
| Heater Front relay | D22 | temperature_control.py |
| Heater Back relay | D23 | temperature_control.py |
| Tip RTD (MAX31865) | SPI CS D19 | monitor.py, CryoProbe_Temp_Control.py |
| Ceramic RTD (MAX31865) | SPI CS D16 | monitor.py, CryoProbe_Temp_Control.py |
| Relay (valve/heater) | D6 | monitor.py, CryoProbe_Temp_Control.py |
| MCP4725 DAC | I2C 0x62 | temperature_pid_control.py |
| Arduino serial (cap) | /dev/ttyACM0 or ACM1 | monitor.py, thickness_monitor scripts |
