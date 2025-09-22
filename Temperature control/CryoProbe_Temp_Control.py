"""
@Author: Andrei Gogosha, Peter Knauss, Melissa Medina-P.
Python file to run the temperature control of the CryoProbe.
Need to update PID control values for faster loop execution.
Works with 3 Adafruit MAX31865 digital converters, a 8-relay and a Sensirion SFM 3000 200C flow meter.
"""

import time
import csv
import keyboard
import os
import board
import digitalio
import adafruit_max31865
import PID
from datetime import datetime as dt
from datetime import timedelta
import serial
import numpy as np
import signal
import sys
import traceback
import busio

def log_temps(f_name,header,data):
    with open(os.path.join(ROOT_DIR, 'Logs', f_name), 'a', encoding='UTF8', newline='') as log_file:
        temp_log_w=csv.writer(log_file)
        temp_log_w.writerow(data)

def open_file(file_name,data_header):
    #Open the log file in the Log subfolder of the working directory with the specified filename
    log_file = open(os.path.join(ROOT_DIR, 'Logs', file_name),'w',encoding='UTF8', newline='')     
    temp_log_w = csv.writer(log_file)
    #Writes the data header for the csv file
    temp_log_w.writerow(data_header)     
    #Returns the log file so it can be saved as a variable and manipulated later
    return log_file     

def calibrated_temps(temp, TC):
    #if temp > 35:
    #    raise Exception('Temperature has reached too high on TC {}'.format(TC))
    if 'Tip' in TC:
        RawRange = 179.8
        ReferenceRange = 169.3
        ActualTemp = (((temp + 159.6) * ReferenceRange) / RawRange) - 150.7
    if 'Ceramic' in TC:
        RawRange = 179.7
        ReferenceRange = 169.5
        ActualTemp = (((temp + 159.9) * ReferenceRange) / RawRange) - 150.9
    if 'Flange' in TC:
        RawRange = 1797
        ReferenceRange = 169.1
        ActualTemp = (((temp + 159.6) * ReferenceRange) / RawRange) - 149.2
        
    return ActualTemp
    
def signal_handler(signum, frame):
    raise KeyboardInterrupt
    
# Raspberry Pi had unreliable Ctrl-C handling, catch independently
signal.signal(signal.SIGINT, signal_handler) 

if __name__ == '__main__':
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CryoProbe_Temp_Control.py")))

    data_f_name = 'Temp_log_{}.csv'.format(dt.now().strftime('%m-%d-%Y-%H-%M'))
    data_header = ['Real time \t' + 'Temp_Tip \t' + 'Temp_Ceramic \t' + 'temp_Flange \t' + 'N2 Flow \t'+ 'MV \t']
    log_file = open_file(data_f_name,data_header)

    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()
    
    #Create flowmeter, communicating over the board's default I2C bus
    ser = serial.Serial('/dev/ttyACM0','115200', timeout = 1)
    ser.flush()
    #Scale factor for Nitrogen
    SF = 140
    #Offset flow
    OF = 32000
    
    # allocate a CS pin and set the direction
    cs16 = digitalio.DigitalInOut(board.D16) #Tip
    cs19 = digitalio.DigitalInOut(board.D19) #Ceramic
    cs21 = digitalio.DigitalInOut(board.D21) #Flange
    Relay = digitalio.DigitalInOut(board.D6) #Relay
    Relay.direction= digitalio.Direction.OUTPUT
    
    #Create a thermocouple object with the above pin assignements
    Tip = adafruit_max31865.MAX31865(spi, cs16, wires = 2)
    Ceramic = adafruit_max31865.MAX31865(spi, cs19, wires = 2)   
    Flange = adafruit_max31865.MAX31865(spi, cs21, wires = 2)   

    #Close valve
    Relay.value = True 
    Rel_status = 11
    #Open valve
    Relay.value = False 
    Rel_status = 10
    
    #Initial inputs for PID control
    #Target temperature
    targetT1 = -130
    
    P1 = 0.2*0.6
    I1 = 1.2*0.2/60
    D1 = 3*0.2*60/40
    
    #Create PID control
    controllerF = PID.PID(P1, I1, D1)
    
    #Initialize the controller        
    controllerF.SetPoint = targetT1             
    controllerF.setSampleTime(0.25)

    Ledger=np.array([[], [], [], [], [], []])
    
    #try and except statement used to catch error and log them to a specified file
    try:     
        runlen = 1
        #set time for loop in seconds
        loop_time = 0.2 
        #number of loops that get averaged to the log
        itt_len = 15 
        # keep track of when the loop starts so that we keep a consistant loop runtime
        start_time = time.time() 
            
        #Keeps doing the loop
        while True:
            
            print('**********************')
            
            #checks if the current log file is 4Mb, if it is it creates a new log file
            #if os.stat(os.path.join(ROOT_DIR, 'Logs', data_f_name)).st_size>= 4194304:      
            #    data_f_name='Temp_log_{}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
            #    log_file.close()
            #    log_file = open_file(data_f_name, data_header)
            
            #Reads the tip, ceramic and flange temperatures
            #Tip.initiate_one_shot_measurement()
            #Ceramic.initiate_one_shot_measurement()
            #Flange.initiate_one_shot_measurement()
            #print(Tip.unpack_temperature(), ' ', Ceramic.unpack_temperature(), ' ', Flange.unpack_temperature())
            #Tip._wait_for_oneshot()
            
            #Flow measurement
            ser.flush()
            ser.flushInput()
            ser.flushOutput()
            #flow = ser.readline().decode('utf-8')
            flow = 0
            #flow = (rawflow-SF)/OF
            
            end_time = time.time()
            
            #Calculate elapsed time
            elapsed_time = end_time - start_time
            #Sets elapsed time in a format 00:00:00
            elapsed_time = str(timedelta(seconds = elapsed_time))
            
            #Print data
            print('N2 Flow:', flow , 'slm' )
            print('Time:', elapsed_time, 'sec')
            print('Tip:', round(Tip.temperature,3), 'C')
            print('Ceramic:', round(Ceramic.temperature,3), 'C')
            print('Flange:', round(Flange.temperature,3), 'C')
            
            temp_Tip = Tip.temperature #calibrated_temps(Tip.temperature, 'Tip')
            temp_Ceramic = Ceramic.temperature #calibrated_temps(Ceramic.temperature,'Ceramic')
            temp_Flange = Flange.temperature #calibrated_temps(Flange.temperature,'Flange')
            
            #Update the pid controlers
            controllerF.update(temp_Tip) 

            MV1 = 10
            MV1 = controllerF.output # get the new pid values
            print('MV:', MV1)
            
            #Write to temp log file
            log_temps(data_f_name, data_header,[elapsed_time, round(Tip.temperature,3) , round(Ceramic.temperature,3), round(Flange.temperature,3), flow, round(MV1,3)])    
            #log_file.flush()
            
            #temp too low, close valve
            if MV1 > 0:      
                Relay.value = True
                Rel_status = 11
            #High temp, open valve
            else:     
                Relay.value = False
                Rel_status = 10
                
            #timestamp used for x axis tick
            #time_stamp= dt.now().strftime('%H:%M:%S')  
              
            Ledger=np.append(Ledger, [[elapsed_time], [temp_Tip], [temp_Ceramic], [temp_Flange], [flow], [MV1]], axis=1)
            
            #change to be however many itterations you want before updating logs
            if runlen==itt_len:     
                Tip_avg=np.average(Ledger[1,-itt_len:].astype('float32'))
                Ceramic_avg=np.average(Ledger[2,-itt_len:].astype('float32'))
                Flange_avg=np.average(Ledger[3,-itt_len:].astype('float32'))
                #write to temp log file
                log_temps(data_f_name,data_header,[elapsed_time, Tip_avg, Ceramic_avg, Flange_avg, flow])     
                #pushes the data collected this loop to the csv.
                log_file.flush() 
                runlen = 0
            
            #only holds onto last itt len +1 temperatures in memory
            if len(Ledger[1])>=itt_len+1:     
                Ledger=np.delete(Ledger, obj=0,axis=1)
            #t4=time.time()
            #print(t2-t1,t4-t3,elapsed)
            #print('{}, {}, {}'.format(Tip.temperature, Ceramic.temperature, Flange.temperature))
            #print(Ledger[:,-1:])
            runlen += 1
            # how long was it running?
            elapsed = time.time() - start_time
            #make loop run every 0.25 seconds 
            if elapsed < loop_time: time.sleep(loop_time-elapsed) 
            else: time.sleep(0.1)
            
    #Opens the relay when program interrupted and writes to error log if need be
    except KeyboardInterrupt:
        print('\n')
        print('Interrupted')
    except Exception as e:
        if not os.path.exists(os.path.join(ROOT_DIR, 'Logs', 'Error Logs')):
            with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'w', encoding='UTF-8') as file:
                file.write('')
        with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'a', encoding='UTF-8') as file:
            file.write('-------------------------------------------------'+'\n')
            file.write(dt.now().strftime('%Y-%m-%d %H:%M:%S')+'\n')
            traceback.print_exc(file=file)
            file.write('\n')
        traceback.print_exc()
    #finally:
        #Relay.value = False

        
