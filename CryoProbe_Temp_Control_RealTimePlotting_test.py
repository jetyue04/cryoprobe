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

# ------------------ Utility Functions ------------------
def log_temps(f_name, data):
    with open(os.path.join(ROOT_DIR, "Logs", f_name), "a", encoding="UTF8", newline="") as log_file:
        temp_log_w = csv.writer(log_file)
        temp_log_w.writerow(data)

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
    # if "Flange" in TC:
    #     RawRange = 1797
    #     ReferenceRange = 169.1
    #     ActualTemp = (((temp + 159.6) * ReferenceRange) / RawRange) - 149.2
    return ActualTemp

def signal_handler(signum, frame):
    raise KeyboardInterrupt

# Raspberry Pi had unreliable Ctrl-C handling, catch independently
signal.signal(signal.SIGINT, signal_handler)

# ------------------ Main ------------------
if __name__ == "__main__":
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CryoProbe_Temp_Control.py")))

    data_f_name = "Temp_log_{}.csv".format(dt.now().strftime("%m-%d-%Y-%H-%M"))
    data_header = ["Real time", "Temp_Tip", "Temp_Ceramic", "MV"]
    log_file = open_file(data_f_name, data_header)

    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # Create flowmeter (disabled)
    # ser = serial.Serial('/dev/ttyACM0','115200', timeout = 1)
    # ser.flush()
    # SF = 140
    # OF = 32000

    # allocate a CS pin and set the direction
    cs19 = digitalio.DigitalInOut(board.D19)  # Tip
    cs16 = digitalio.DigitalInOut(board.D16)  # Ceramic
    # cs21 = digitalio.DigitalInOut(board.D21)  # Flange
    Relay = digitalio.DigitalInOut(board.D6)  # Relay
    Relay.direction = digitalio.Direction.OUTPUT

    # Create thermocouple objects
    Tip = adafruit_max31865.MAX31865(spi, cs19, wires=2)
    Ceramic = adafruit_max31865.MAX31865(spi, cs16, wires=2)
    # Flange = adafruit_max31865.MAX31865(spi, cs21, wires=2)

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

    Ledger = np.array([[], [], [], []])

    # Data storage for plotting
    time_data, tip_data, ceramic_data = [], [], []
    start_time = time.time()

    # Plot setup
    fig, ax = plt.subplots()
    line1, = ax.plot([], [], "b-", label="Tip Temperature")
    line2, = ax.plot([], [], "r-", label="Ceramic Temperature")
    # line3, = ax.plot([], [], "g-", label="Flange Temperature")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Real-Time Slow Control Cryogenic Probe")
    ax.legend()

    #def update_plot(frame):
     #   line1.set_data(time_data, tip_data)
     #   line2.set_data(time_data, ceramic_data)
        # line3.set_data(time_data, flange_data)

      #  if time_data:
            #ax.set_xlim(time_data[0], time_data[-1])
     #       all_data = tip_data + ceramic_data  # + flange_data
      #      ax.set_ylim(min(all_data) - 5, max(all_data) + 5)
     #   return line1, line2

    #ani = FuncAnimation(fig, update_plot, interval=100, blit=False)
    plt.show(block=False)

    # ------------------ Control Loop ------------------
    try:
        runlen = 1
        loop_time = 0.2
        itt_len = 15
        start_time = time.time()

        while True:
            end_time = time.time()
            elapsed_time = str(timedelta(seconds=end_time - start_time))

            temp_Tip = Tip.temperature
            temp_Ceramic = Ceramic.temperature
            # temp_Flange = Flange.temperature

            controllerF.update(temp_Tip)
            MV1 = controllerF.output

            print("Time:", elapsed_time)
            print("Tip:", round(temp_Tip, 3), "C")
            print("Ceramic:", round(temp_Ceramic, 3), "C")
            print("MV:", MV1)

            # Append data
            current_time = time.time() - start_time
            time_data.append(current_time)
            tip_data.append(temp_Tip)
            ceramic_data.append(temp_Ceramic)
            line1.set_data(time_data, tip_data)
            line2.set_data(time_data, ceramic_data)
            ax.relim()
            ax.autoscale_view()
            plt.pause(0.01)

            # Log data
            log_temps(data_f_name, [elapsed_time, round(temp_Tip, 3), round(temp_Ceramic, 3), round(MV1, 3)])

            # Relay control
            if MV1 > 0:
                Relay.value = True
            else:
                Relay.value = False

            # Maintain timing
            elapsed = time.time() - end_time
            if elapsed < loop_time:
                time.sleep(loop_time - elapsed)

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
