import serial
import os
import time
from datetime import datetime as dt
from datetime import timedelta
import csv

# Initialize serial connection
ser = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=1)
ser.flush()
ser.flushInput()  # Flush any data in the input buffer
ser.flushOutput()  # Flush any data in the output buffer

# Set window size and initialize data arrays
window_size = 20  # Last 20 seconds
y_var = [0] * window_size  # Store capacitance values
x_var = [0] * window_size  # Store corresponding timestamps (elapsed time)

# Initialize global data lists
time_data = []
cap_data = []

# Opens file
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CapSerial_modified.py")))
data_f_name = 'Cap_Serial_{}.csv'.format(dt.now().strftime('%m-%d-%Y-%H-%M-%S'))
data_header = ['Real time \t' + 'Capacitance \t']
log_file = open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'w', encoding='UTF8', newline='')
cap_log_w = csv.writer(log_file)
cap_log_w.writerow(data_header)

def log_cap(data):
    with open(os.path.join(ROOT_DIR, 'Logs', data_f_name), 'a', encoding='UTF8', newline='') as log_file:
        cap_log_w = csv.writer(log_file)
        cap_log_w.writerow(data)

start_time = time.time()

def update():
    global y_var, x_var

    try:
        ser_bytes = ser.readline()  # Read a line of data from the serial port

        # Debugging: Print raw bytes to inspect what is received
        print(f"Raw bytes received: {ser_bytes}")

        # Check if the received data is not empty or None
        if not ser_bytes or ser_bytes == b'':
            print("No data received.")
            return  # Skip the current iteration if no data is received

        str_value = ser_bytes.decode('utf-8').strip()  # Decode the byte data into a string

        # Debugging: Print the decoded string value
        print(f"Decoded string: {str_value}")

        # If the data includes 'Value :', remove that part and convert the remaining part to an integer
        if str_value.startswith("Value:"):
            str_value = str_value.replace("Value:", "").strip()

        # Initialize 'value' only if valid data is present
        try:
            value = int(str_value)  # Attempt to convert the value to an integer
            print(f"Extracted value: {value}")
        except ValueError:
            print(f"Invalid data received: {ser_bytes}")
            return  # Skip the current iteration if the value is not valid

        # Calculate capacitance
        cap = round((value - 12288) / 40944 * 4, 5)

        # Update capacitance data
        y_var = y_var[1:]  # Remove the first element to shift the array
        y_var.append(cap)  # Add new value to the end

        # Update time data (real-time)
        elapsed_time = time.time() - start_time
        elapsed_time_formatted = str(timedelta(seconds=elapsed_time))  # Format as mm:ss

        # Update time data for x-axis (last 20 seconds)
        x_var = x_var[1:]  # Remove the first element to shift the array
        x_var.append(elapsed_time)  # Add new time to the end
        
        # Log data
        log_cap([elapsed_time_formatted, cap])

        # Clear the console and print the updated values
        print("\033c", end="")  # This clears the terminal screen
        print(f"Time: {elapsed_time_formatted[-5:]}")
        print(f"Capacitance: {cap} pF")
        
    except Exception as e:
        print(f"Error processing data: {e}")
    
    # Call the update function every 1 second (1000ms)
    time.sleep(1)
    update()

# Start the update process
update()

# Close the serial connection when done
ser.close()








