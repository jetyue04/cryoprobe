import serial
import os
import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk
from datetime import datetime as dt, timedelta

# ------------------ Serial Setup ------------------
ser = serial.Serial(port='/dev/ttyACM1', baudrate=9600, timeout=1)

# ------------------ Tkinter Setup -----------------
root = tk.Tk()
root.title("Capacitance Monitor")

cap_label = ttk.Label(root, text="Capacitance: --- pF", font=("Arial", 14))
cap_label.pack(pady=10)

# ------------------ Plot Setup --------------------
fig = Figure(figsize=(7, 4), dpi=100)
ax = fig.add_subplot(111)
line, = ax.plot([], [], '-', label='Capacitance')
ax.set_xlabel("Time (s)")
ax.set_ylabel("Capacitance (pF)")
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# ------------------ Data Buffers ------------------
window_size = 200
y_data = np.zeros(window_size)
x_data = np.zeros(window_size)
start_time = time.time()

# ------------------ File Logging ------------------
log_dir = os.path.join(os.getcwd(), "Logs")
os.makedirs(log_dir, exist_ok=True)
filename = f"Cap_Serial_{dt.now().strftime('%m-%d-%Y-%H-%M-%S')}.csv"
filepath = os.path.join(log_dir, filename)

# Write header: all four Arduino fields + timestamp
with open(filepath, 'w', newline='', encoding='UTF8') as f:
    writer = csv.writer(f)
    writer.writerow(['Time', 'ADC', 'CAPDAC', 'InputRange', 'Capacitance'])

def log_row(elapsed, adc, capdac, ir, cap):
    with open(filepath, 'a', newline='', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([elapsed, adc, capdac, ir, cap])

# ------------------ Update Function ----------------
def update(frame):
    global y_data, x_data

    try:
        line_str = ser.readline().decode().strip()
        if not line_str or line_str.startswith("ADC"):  # skip Arduino header
            return

        # Parse Arduino CSV line
        parts = line_str.split(",")
        if len(parts) != 4:
            return

        adc, capdac, ir, cap = parts
        adc, capdac, ir, cap = int(adc), int(capdac), float(ir), float(cap)

        # Update buffers
        elapsed = time.time() - start_time
        y_data = np.roll(y_data, -1); y_data[-1] = cap
        x_data = np.roll(x_data, -1); x_data[-1] = elapsed

        # Rolling stats (ignore zeros at startup)
        valid = y_data[y_data != 0]
        cap_avg = np.mean(valid) if valid.size else 0
        cap_std = np.std(valid) if valid.size else 0

        # Update label
        cap_label.config(
            text=f"Capacitance: {cap:.5f} pF\n"
                 f"Rolling Avg: {cap_avg:.5f} pF\n"
                 f"Rolling Std: {cap_std:.5f} pF"
        )

        # Log everything
        log_row(str(timedelta(seconds=int(elapsed))), adc, capdac, ir, cap)

        # Update plot
        line.set_ydata(y_data)
        line.set_xdata(x_data - x_data[0])
        ax.set_xlim(0, max(20, x_data[-1] - x_data[0]))
        ax.set_ylim(min(y_data) - 0.5, max(y_data) + 0.5)
        ax.legend()
        canvas.draw()

    except Exception:
        pass

# ------------------ Animation ----------------------
ani = FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)

# ------------------ Mainloop -----------------------
root.mainloop()
ser.close()
