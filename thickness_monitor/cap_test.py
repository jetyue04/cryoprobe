import serial
import time
import matplotlib.pyplot as plt
import csv
from datetime import datetime
import os

# ---------------- SETTINGS ----------------
PORT = "/dev/cu.usbmodem1201"
BAUD = 9600
# ------------------------------------------

# ----- Serial -----
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # allow Arduino reset

# ----- Logging -----
os.makedirs("Logs", exist_ok=True)

filename = os.path.join(
    "Logs",
    f"cap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)

log_file = open(filename, "w", newline="")
writer = csv.writer(log_file)

writer.writerow([
    "Time (s)",
    "ADC",
    "CAPDAC",
    "InputRange",
    "Capacitance"
])

print(f"Logging to {filename}")

# Storage
t_data = []
cap_data = []

start_time = time.time()

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot([], [], label="Capacitance")

ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance")
ax.legend()

print("Listening to serial...")

try:
    while True:

        line_raw = ser.readline().decode("utf-8").strip()

        if not line_raw:
            continue

        # Skip header if present
        if "ADC" in line_raw:
            continue

        try:
            parts = line_raw.split(",")

            adc = float(parts[0])
            capdac = float(parts[1])
            input_range = float(parts[2])
            capacitance = float(parts[3])

        except:
            print("Bad line:", line_raw)
            continue

        # Store time series
        current_time = time.time() - start_time
        t_data.append(current_time)
        cap_data.append(capacitance)

        print(current_time, capacitance)

        # ----- Log to CSV -----
        writer.writerow([
            round(current_time, 3),
            adc,
            capdac,
            input_range,
            capacitance
        ])
        log_file.flush()   # ensures file writes live

        # Update plot
        line.set_data(t_data, cap_data)
        ax.relim()
        ax.autoscale_view()

        plt.pause(0.01)
        
        # time.sleep(0.25)


except KeyboardInterrupt:
    print("Stopped")

finally:
    ser.close()
    log_file.close()
    print("File saved and serial closed.")
