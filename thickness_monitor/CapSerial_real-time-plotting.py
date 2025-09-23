import serial
import os
import time
from datetime import datetime as dt, timedelta
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk

# Initialize serial connection
ser = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=1)
ser.flush()
ser.flushInput()
ser.flushOutput()

# Tkinter setup
root = tk.Tk()
root.title("Real-time Capacitance Monitor")

# Add label to show capacitance
cap_label = ttk.Label(root, text="Capacitance: --- pF", font=("Arial", 14))
cap_label.pack(pady=10)

# Create a Figure object for the plot
fig = Figure(figsize=(7, 4), dpi=100)
ax = fig.add_subplot(111)
line1, = ax.plot([], [], '-', label='Capacitance')

ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
ax.set_title("Real-time Capacitance Measurement")

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Initialize data arrays
window_size = 200
y_var = np.zeros(window_size)
x_var = np.zeros(window_size)

# File setup
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CapSerial_modified.py")))
data_f_name = 'Cap_Serial_{}.csv'.format(dt.now().strftime('%m-%d-%Y-%H-%M-%S'))
data_header = ['Real time', 'Capacitance']
log_file = open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'w', encoding='UTF8', newline='')
cap_log_w = csv.writer(log_file, delimiter='\t')
cap_log_w.writerow(data_header)

def log_cap(data):
    with open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'a', encoding='UTF8', newline='') as log_file:
        cap_log_w = csv.writer(log_file, delimiter='\t')
        cap_log_w.writerow(data)

i = 0
#baseline_raw = 0
IR = 4 #Input range
SCALE = 40944
#DAC = 8
OFFSET = 12288
#OFFSET = 12288 + ((40944-12288)/64)*DAC

start_time = time.time()

def update(frame):
    global y_var, x_var, i
    try:
        ser_bytes = ser.readline()
        if not ser_bytes or ser_bytes == b'':
            return

        str_value = ser_bytes.decode('utf-8').strip()
        if str_value.startswith("Value :"):
            str_value = str_value.replace("Value :", "").strip()

        try:
            value = int(str_value)
        except ValueError:
            return

        i += 1
        if i == 10:
            #baseline_raw = value
            cap_baseline = round((value - OFFSET) / SCALE * IR, 5)
            print(f"[CALIBRATION] Baseline value set to: {cap_baseline}")
            return
        print(f"Raw value: {value}")

        cap = round(((value - OFFSET) / SCALE) * IR, 5)

        # Update label text
        cap_label.config(text=f"Capacitance: {cap:.5f} pF")

        y_var = np.roll(y_var, -1)
        y_var[-1] = cap

        elapsed_time = time.time() - start_time
        elapsed_time_formatted = str(timedelta(seconds=elapsed_time))

        x_var = np.roll(x_var, -1)
        x_var[-1] = elapsed_time

        log_cap([elapsed_time_formatted, cap])

        line1.set_ydata(y_var)
        line1.set_xdata(x_var - x_var[0])

        ax.set_xlim(0, 20)
        ax.set_ylim(min(y_var) - 0.5, max(y_var) + 0.5)

        tick_positions = np.linspace(x_var[0], x_var[-1], num=6)
        tick_labels = [str(timedelta(seconds=int(tick)))[-5:] for tick in tick_positions]
        ax.set_xticks(tick_positions - x_var[0])
        ax.set_xticklabels(tick_labels)

        ax.legend()
        canvas.draw()

    except ValueError:
        pass

# Start animation
ani = FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)

# Run the Tkinter main loop
root.mainloop()

# Close serial connection when done
ser.close()
