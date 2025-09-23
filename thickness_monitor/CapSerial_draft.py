import serial
import os
import time
from datetime import datetime as dt
from datetime import timedelta
import csv
import matplotlib.pyplot as plt
#matplotlib.use("tkAgg")
import numpy as np
from matplotlib.animation import FuncAnimation

# Initialize serial connection
ser = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=1)
ser.flush
ser.flushInput()
ser.flushOutput()

# Set window size and initialize data arrays
plot_window = 100
y_var = np.zeros(plot_window) 
x_var = np.zeros(plot_window) 
#y_var = np.array(np.zeros([plot_window]))
#x_var = [dt.now().strftime('%M:%S')]*plot_window

#np.array(np.zeros([plot_window]))
#for i in range(plot_window):
    #x_var.append(dt.now().strftime('%M:%S'))
    #x_var.append(time.asctime(time.time()))

#ax.locator_params(tight=True, nbins=4)
# Customize the x-tick positions and labels

#Initialize global data lists
time_data = []
cap_data = []

fig, ax = plt.subplots()
line1,  = ax.plot([], [], '-o', label='Tip')

ax.set_xlabel("Time (m:s)")
ax.set_ylabel("Capacitance (F)")
ax.set_title("Real-time Capacitance Measurement")

#ax.set_xticks(range(0, plot_window, 10))  # Set tick positions at intervals of 10
#ax.set_xticklabels([dt.now().strftime('%M:%S') for _ in range(0, plot_window, 10)])
#ax.set_xticklabels(x_var[::10])  # Use corresponding time labels from x_var

#Opens file
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CapSerial_modified.py")))
data_f_name = 'Cap_Serial_{}.csv'.format(dt.now().strftime('%m-%d-%Y-%H-%M-%S'))
data_header = ['Real time \t' + 'Capacitance \t']
log_file = log_file = open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'w', encoding='UTF8', newline='')
cap_log_w=csv.writer(log_file)
cap_log_w.writerow(data_header)

def log_cap(data):
        with open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'a', encoding='UTF8', newline='') as log_file:
                cap_log_w=csv.writer(log_file)
                cap_log_w.writerow(data)

#def open_file(file_name,data_header):
        #Open the log file in the Log subfolder of the working directory with the specified filename
        #log_file = open(os.path.join(ROOT_DIR, 'Logs', file_name),'w',encoding='UTF8', newline='')     
        #cap_log_w = csv.writer(log_file)
        #Writes the data header for the csv file
        #cap_log_w.writerow(data_header)     
        #Returns the log file so it can be saved as a variable and manipulated later
        #return log_file 

#Ledger=np.array([[], []])
start_time = time.time()

def update(frame):

        global y_var, x_var

# Main loop to read serial data and update plot
#while True:
        try:
                
                ser_bytes = ser.readline()
                
                print('**********************')
                print(f"Raw bytes: {ser_bytes}")
                #elapsed_time_str = str(timedelta(seconds=elapsed_time))
                #print(elapsed_time_str)
                #value = int(ser_bytes.strip())
                #value = int(ser_bytes.decode('utf-8').strip())
                # Strip the newline and carriage return characters and decode the byte sequence to a string
                str_value = ser_bytes.decode('utf-8').strip()

                # If the data includes 'Value :', remove that part and convert the remaining part to an integer
                if str_value.startswith("Value :"):
                    str_value = str_value.replace("Value :", "").strip()

                # Now try converting the extracted numeric string to an integer
                try:
                    value = int(str_value)
                    print(f"Extracted Value: {value}")
                except ValueError:
                    print(f"Invalid data received: {ser_bytes}")
                    
                #value = int.from_bytes(ser_bytes[:2],byteorder='little')
 
                cap = round((value - 12288)/40944*4,5)
                print(f"Capacitance: {cap} pF")
                #y_var = np.append(y_var, cap)
                y_var = np.roll(y_var,-1)
                #x_var.append(dt.now().strftime('%M:%S'))
                y_var[-1] = cap
                #y_var = y_var[1: plot_window + 1]
                x_var = np.roll(x_var,-1)
                elapsed_time=time.time()-start_time
                #Sets elapsed time in a format 00:00:00
                elapsed_time_formatted = str(timedelta(seconds = elapsed_time))
                print(f"Time: {elapsed_time_formatted}")
                #x_var = [elapsed_time]*plot_window
                #x_var[-1] = dt.now().strftime('%M:%S')
                x_var[-1] = elapsed_time
                
                #log_cap(data_f_name, data_header,[elapsed_time, cap])
                log_cap([elapsed_time_formatted, cap])    
                #Ledger=np.append(Ledger, [[elapsed_time], [cap]], axis=1)
                
                        
                #print(dt.now().strftime('%M:%S'))
                line1.set_ydata(y_var)
                line1.set_xdata(x_var)
                ax.relim()
                ax.autoscale_view()
                
                if len(x_var) > 1:
                    x_min = min(x_var)
                    x_max = max(x_var)
                    # Expand the range if limits are the same
                    if x_max == x_min:
                        x_max += 1  
                #ax.set_xlim(x_min, x_max)
                # Adjust tick intervals as needed
                #ax.set_xticklabels([str(timedelta(seconds=int(x))) for x in x_var[::10]])
                #Rotate x labels for better readability
                #plt.xticks(rotation=45)
                # Limit the x-axis based on the plot window size
                #ax.set_xlim(0, plot_window)
                    
                #Autoscale the y_min and y_max values based on data
                y_min = min(y_var) - 3
                y_max = max(y_var) + 3
                # Set y-axis range as needed    
                ax.set_ylim(y_min, y_max)  
                plt.legend()

        except ValueError:
                print(f"Invalid data received: {ser_bytes}")

# Create an animated plot using FuncAnimation
ani = FuncAnimation(fig, update, interval=1000,cache_frame_data=False)  # Update every 1000ms (1 second)

# Show the plot
plt.legend()
plt.show()

ser.close()
