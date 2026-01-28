"""
@Author: Andrei Gogosha, Peter Knauss, Melissa Medina-P.
Python file to run the temperature control of the CryoProbe.
Need to update PID control values for faster loop execution.
Works with 3 Adafruit MAX31865 digital converters, a 8-relay and a Sensirion SFM 3000 200C flow meter.
"""

import time
import csv
import os
import board
import digitalio
import adafruit_max31865
import PID
from datetime import datetime as dt, timedelta
import numpy as np
import signal
import traceback
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import serial
from collections import deque


# ------------------ Utility Functions ------------------
def log_temps(f_name, data):
    with open(os.path.join(ROOT_DIR, "Logs", f_name), "a", encoding="UTF8", newline="") as log_file:
        csv_writer = csv.writer(log_file)
        csv_writer.writerow(data)

def open_file(file_name, data_header):
    os.makedirs(os.path.join(ROOT_DIR, "Logs"), exist_ok=True)
    log_file = open(os.path.join(ROOT_DIR, "Logs", file_name), "w", encoding="UTF8", newline="")
    temp_log_w = csv.writer(log_file)
    temp_log_w.writerow(data_header)
    return log_file

def calibrated_temps(temp, TC):
    if "Tip" in TC:
        RawRange = 179.8
        ReferenceRange = 169.3
        ActualTemp = (((temp + 159.6) * ReferenceRange) / RawRange) - 150.7
    if "Ceramic" in TC:
        RawRange = 179.7
        ReferenceRange = 169.5
        ActualTemp = (((temp + 159.9) * ReferenceRange) / RawRange) - 150.9
    return ActualTemp

def signal_handler(signum, frame):
    raise KeyboardInterrupt

# Raspberry Pi had unreliable Ctrl-C handling, catch independently
signal.signal(signal.SIGINT, signal_handler)

# ------------------ Main ------------------
if __name__ == "__main__":
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CryoProbe_Temp_Control.py")))

    data_f_name = "Real_time_log_{}.csv".format(dt.now().strftime("%m-%d-%Y-%H-%M"))
    data_header = ["Real time", "Temp_Tip", "Temp_Ceramic", "MV", 'ADC', 'CAPDAC', 'InputRange', 'Capacitance']
    log_file = open_file(data_f_name, data_header)

    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # allocate a CS pin and set the direction
    cs19 = digitalio.DigitalInOut(board.D19)  # Tip
    cs16 = digitalio.DigitalInOut(board.D16)  # Ceramic
    Relay = digitalio.DigitalInOut(board.D6)  # Relay
    Relay.direction = digitalio.Direction.OUTPUT

    # Create thermocouple objects
    Tip = adafruit_max31865.MAX31865(spi, cs19, wires=2)
    Ceramic = adafruit_max31865.MAX31865(spi, cs16, wires=2)

    # Initialize Cap reading/Serial Set up
    ser = serial.Serial(port='/dev/ttyACM1', baudrate=9600, timeout=1)

    # Close valve
    Relay.value = True
    # Open valve
    Relay.value = False

    # PID setup
    targetT1 = -110
    P1 = 0.2 * 0.6
    I1 = 1.2 * 0.2 / 60
    D1 = 3 * 0.2 * 60 / 40

    controllerF = PID.PID(P1, I1, D1)
    controllerF.SetPoint = targetT1
    controllerF.setSampleTime(0.25)

    # Ledger = np.array([[], [], [], []])

    # Initialize arrays for plotting
    window_size = 200  # number of points to display
    time_data = deque(maxlen=window_size)
    tip_data = deque(maxlen=window_size)
    ceramic_data = deque(maxlen=window_size)
    cap_data = deque(maxlen=window_size)

    # time_data, tip_data, ceramic_data = [], [], []
    start_time = time.time()

    # ------------------ Plotting Setup ------------------
    fig, (ax_temp, ax_cap) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    # Temperature lines
    line_tip, = ax_temp.plot([], [], "b-", label="Tip Temperature")
    line_ceramic, = ax_temp.plot([], [], "r-", label="Ceramic Temperature")
    ax_temp.set_ylabel("Temperature (°C)")
    ax_temp.legend()
    ax_temp.set_title("CryoProbe Real-Time Monitoring")

    # Capacitance line
    line_cap, = ax_cap.plot([], [], "g-", label="Capacitance (pF)")
    ax_cap.set_xlabel("Time (s)")
    ax_cap.set_ylabel("Capacitance (pF)")
    ax_cap.legend()

    plt.tight_layout()
    plt.show(block=False)

    def update_plot():
        line_tip.set_data(time_data, tip_data)
        line_ceramic.set_data(time_data, ceramic_data)
        line_cap.set_data(time_data, cap_data)

        # ax_temp.relim()
        # ax_temp.autoscale_view()
        # ax_cap.relim()
        # ax_cap.autoscale_view()

        # X-axis rolling window
        if time_data:
            ax_temp.set_xlim(time_data[0], time_data[-1])
            ax_cap.set_xlim(time_data[0], time_data[-1])

        # Y-axis ±1 around current min/max
        if tip_data and ceramic_data:
            t_min = min(min(tip_data), min(ceramic_data))
            t_max = max(max(tip_data), max(ceramic_data))
            ax_temp.set_ylim(t_min - 1, t_max + 1)

        if cap_data:
            c_min = min(cap_data)
            c_max = max(cap_data)
            ax_cap.set_ylim(c_min - 1, c_max + 1)

        plt.pause(0.01)

    # ------------------ Control Loop ------------------
    try:
        runlen = 1
        # loop_time = 0.2
        itt_len = 15
        start_time = time.time()

        while True:
            end_time = time.time()
            elapsed_time = str(timedelta(seconds=end_time - start_time))

            #Read Temperature
            temp_Tip = Tip.temperature
            temp_Ceramic = Ceramic.temperature
            controllerF.update(temp_Tip)
            MV1 = controllerF.output

            # Read capacitance data from Arduino
            line_str = ser.readline().decode().strip()
            if not line_str or line_str.startswith("ADC"):  # skip Arduino header
                continue

            # Parse Arduino CSV line
            parts = line_str.split(",")
            if len(parts) != 4:
                continue

            adc, capdac, ir, cap = parts
            adc, capdac, ir, cap = int(adc), int(capdac), float(ir), float(cap)

            print("Time:", elapsed_time)
            print("Tip:", round(temp_Tip, 3), "C")
            print("Ceramic:", round(temp_Ceramic, 3), "C")
            print("MV:", MV1)
            print("ADC:", adc)
            print("CAPDAC:", capdac)
            print("InputRange:", ir)
            print("Capacitance:", cap, "pF")
            print("-------------------------------")

            # Append data
            current_time = time.time() - start_time
            time_data.append(current_time)
            tip_data.append(temp_Tip)
            ceramic_data.append(temp_Ceramic)
            cap_data.append(cap)

            #Update plot
            update_plot()

            # Log data
            log_temps(data_f_name, [elapsed_time, round(temp_Tip, 3), round(temp_Ceramic, 3), round(MV1, 3), adc, capdac, ir, cap])

            # Relay control
            if MV1 > 0:
                Relay.value = True
            else:
                Relay.value = False

            # # Maintain timing
            # elapsed = time.time() - end_time
            # # if elapsed < loop_time:
            # #     time.sleep(loop_time - elapsed)

    except KeyboardInterrupt:
        print("\nInterrupted")

    except Exception as e:
        os.makedirs(os.path.join(ROOT_DIR, "Logs", "Error Logs"), exist_ok=True)
        with open(os.path.join(ROOT_DIR, "Logs", "Error Logs", "errors.txt"), "a", encoding="UTF-8") as file:
            file.write("-------------------------------------------------\n")
            file.write(dt.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            traceback.print_exc(file=file)
            file.write("\n")
        traceback.print_exc()

    finally:
        Relay.value = False
        log_file.close()
