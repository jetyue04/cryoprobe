import time
import csv
import keyboard
import os
import board 
import busio 
import adafruit_mcp4725
from datetime import datetime as dt
import numpy as np
import traceback
from simple_pid import PID
from collections import deque
import matplotlib.pyplot as plt


# --- Conditional Imports for Mocking ---
if os.environ.get('TEST_MODE') == '1':
    print("Running in TEST_MODE: Using mock hardware modules.")
    from mocks import board, digitalio, adafruit_max31856
else:
    print("Running in NORMAL_MODE: Using actual hardware modules.")
    import board
    import digitalio
    import adafruit_max31856
# --- End Conditional Imports ---

# ... (rest of your functions: log_temps, open_file, calibrated_temps) ...
def log_temps(log_file, data):
    temp_log_w = csv.writer(log_file)
    temp_log_w.writerow(data)

def open_file(file_name, data_header, root_dir):
    log_dir = os.path.join(root_dir, 'Logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(os.path.join(log_dir, file_name), 'w', encoding='UTF8', newline='')
    temp_log_w = csv.writer(log_file)
    temp_log_w.writerow(data_header)
    return log_file

def calibrated_temps(temp, TC):
    ActualTemp = temp
    if TC == 'HeatExB':
        RawRange = 121
        ReferenceRange = 126
        ActualTemp = (((temp + 117) * ReferenceRange) / RawRange) - 108
    elif TC == 'HeatExF':
        RawRange = 184
        ReferenceRange = 179
        ActualTemp = (((temp + 174) * ReferenceRange) / RawRange) - 161
    elif TC == 'ColdHead':
        ActualTemp = temp
    elif TC == 'Chamber':
        ActualTemp = temp + 7.6
    return ActualTemp

if __name__ == '__main__':
    ROOT_DIR = os.path.realpath(os.path.dirname(__file__))

    data_f_name = 'Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M-%S'))
    data_header = ['Rt', 'temp_ch', 'temp_hex_f', 'temp_hex_b', 'temp_chamber', 'heater_voltage']
    log_file = open_file(data_f_name, data_header, ROOT_DIR)

    spi = board.SPI()

    cs13 = digitalio.DigitalInOut(board.D13)
    cs13.direction = digitalio.Direction.OUTPUT
    cs16 = digitalio.DigitalInOut(board.D16)
    cs16.direction = digitalio.Direction.OUTPUT
    cs25 = digitalio.DigitalInOut(board.D25)
    cs25.direction = digitalio.Direction.OUTPUT
    cs26 = digitalio.DigitalInOut(board.D26)
    cs26.direction = digitalio.Direction.OUTPUT
    # HeaterF = digitalio.DigitalInOut(board.D22)
    # HeaterF.direction = digitalio.Direction.OUTPUT
    # HeaterB = digitalio.DigitalInOut(board.D23)
    # HeaterB.direction = digitalio.Direction.OUTPUT

    i2c = busio.I2C(board.SCL, board.SDA)
    dac = adafruit_mcp4725.MCP4725(i2c, address = 0x62)
    P = 0.2 * 0.6
    I = 1.2 * 0.2 / 60
    D = 3 * 0.2 * 60 / 40
    target_temp = -110

    pid = PID(P, I, D)
    pid.setpoint = target_temp
    pid.sample_time = 1.0
    pid.output_limits = (0, 22.5)   #want to set these limits so that the power suppy does not supply over 24 volts to the heaters

    Vmax = 36 # Max voltage of the power supply

    ColdHead = adafruit_max31856.MAX31856(spi, cs13, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
    HeatExF = adafruit_max31856.MAX31856(spi, cs16, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
    HeatExB = adafruit_max31856.MAX31856(spi, cs25, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
    Chamber = adafruit_max31856.MAX31856(spi, cs26, thermocouple_type=adafruit_max31856.ThermocoupleType.T)

    # HeaterF.value = False
    # HeaterB.value = False
    

    data_buffer = []
    itt_len = 6
    
    # Initialize data array for plotting
    window_size = 200
    time_data = deque(maxlen=window_size)
    coldhead_data = deque(maxlen=window_size)
    heatexF_data = deque(maxlen=window_size)
    heatexB_data = deque(maxlen=window_size)
    chamber_data = deque(maxlen=window_size)
    
    start_time = time.time()
    
    #Plot set up
    fig, ax = plt.subplots(figsize=(8,6))
    
    line_coldhead, = ax.plot([], [], "b", label='cold head')
    line_heatexF, = ax.plot([], [], 'r', label='Heat exchange front')
    line_heatexB, = ax.plot([], [], 'g', label='Heat exchange back')
    line_chamber, = ax.plot([], [], 'pink', label='chamber')
    
    ax.set_ylabel('Temperature (C)')
    ax.set_xlabel('Time (s)')
    ax.legend()
    
    plt.show(block=False)
    
    def update_plot():
        
        line_coldhead.set_data(time_data, coldhead_data)
        line_heatexF.set_data(time_data, heatexF_data)
        line_heatexB.set_data(time_data, heatexB_data)
        line_chamber.set_data(time_data, chamber_data)
        
        if len(time_data) > 1:
            ax.set_xlim(time_data[0], time_data[-1])
        
        t_min = min(min(coldhead_data), min(heatexF_data), min(heatexB_data), min(chamber_data))
        t_max = max(max(coldhead_data), max(heatexF_data), max(heatexB_data), max(chamber_data))
        
        ax.set_ylim(t_min-2, t_max+2)
        
        plt.pause(0.01)

    try:
        while True:
            now = time.time()

            if os.stat(os.path.join(ROOT_DIR, 'Logs', data_f_name)).st_size >= 4194304:
                log_file.close()
                data_f_name = 'Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M-%S'))
                log_file = open_file(data_f_name, data_header, ROOT_DIR)

            ColdHead.initiate_one_shot_measurement()
            HeatExF.initiate_one_shot_measurement()
            HeatExB.initiate_one_shot_measurement()
            Chamber.initiate_one_shot_measurement()

            ColdHead._wait_for_oneshot()
            temp_coldhead = calibrated_temps(ColdHead.unpack_temperature(), 'ColdHead')

            HeatExF._wait_for_oneshot()
            temp_HeatExF = calibrated_temps(HeatExF.unpack_temperature(), 'HeatExF')

            HeatExB._wait_for_oneshot()
            temp_HeatExB = calibrated_temps(HeatExB.unpack_temperature(), 'HeatExB')

            Chamber._wait_for_oneshot()
            temp_chamber = calibrated_temps(Chamber.unpack_temperature(), 'Chamber')
            
            #Append data for plotting
            current_time = time.time() - start_time
            time_data.append(current_time)
            coldhead_data.append(temp_coldhead)
            heatexF_data.append(temp_HeatExF)
            heatexB_data.append(temp_HeatExB)
            chamber_data.append(temp_chamber)

            mv = pid(temp_HeatExB)
            input_voltage = round( mv / Vmax * 5)
            bit_12_input = round(min((4095 * input_voltage) / 3.3, 4095 ))
            dac.raw_value = bit_12_input

            #update plot
            update_plot()
            
            time_stamp = dt.now().strftime('%H:%M:%S')

            current_data = [time_stamp, temp_coldhead, temp_HeatExF, temp_HeatExB, temp_chamber, mv]
            print(temp_coldhead, temp_HeatExF, temp_HeatExB, temp_chamber, mv)
            data_buffer.append(current_data)

            if len(data_buffer) > itt_len:
                data_buffer.pop(0)

            if len(data_buffer) == itt_len:
                temps_for_avg = np.array(data_buffer)[:, 1:5].astype(float)
                # mv_f_for_avg = np.array(data_buffer)[:, 5].astype(float)
                # mv_b_for_avg = np.array(data_buffer)[:, 7].astype(float)

                Coldhead_avg = np.average(temps_for_avg[:, 0])
                HeatExF_avg = np.average(temps_for_avg[:, 1])
                HeatExB_avg = np.average(temps_for_avg[:, 2])
                Chamber_avg = np.average(temps_for_avg[:, 3])
            
                log_temps(log_file, [time_stamp, Coldhead_avg, HeatExF_avg, HeatExB_avg, Chamber_avg, mv])
                log_file.flush()
            
            elapsed = time.time() - now
            sleep_duration = 1 - elapsed
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            else:
                time.sleep(0.01)

    except Exception as e:
        # HeaterF.value = False
        # HeaterB.value = False
        dac.raw_value = 0

        if isinstance(e, KeyboardInterrupt):
            print('Program interrupted by user.')
        else:
            print(f"An unexpected error occurred: {e}")
            log_dir = os.path.join(ROOT_DIR, 'Logs')
            os.makedirs(log_dir, exist_ok=True)
            error_log_path = os.path.join(log_dir, 'Error Logs.txt')
            with open(error_log_path, 'a', encoding='UTF-8') as file:
                file.write('-------------------------------------------------\n')
                file.write(dt.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
                traceback.print_exc(file=file)
                file.write('\n')
            traceback.print_exc()

    finally:
        if 'log_file' in locals() and not log_file.closed:
            log_file.close()
        # HeaterF.value = False
        # HeaterB.value = False
        dac.raw_value = 0
        print("Heaters turned off and log file closed.")
