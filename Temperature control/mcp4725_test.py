import time 
import board 
import busio 
import adafruit_mcp4725
from simple_pid import PID

#this is the i2c bus 
i2c = busio.I2C(board.SCL, board.SDA)

#this initialize the dac
dac = adafruit_mcp4725.MCP4725(i2c, address = 0x62)

#using the raw dac value: set the dac value
dac.raw_value = 0

# PID setup
setpoint = -110
p = 0.2
i = 0.01 
d = 0.05
pid = PID(p, i, d)
pid.setpoint = setpoint
pid.sample_time = 1.0
pid.output_limits = (0, 24)   #want to set these limits so that the power suppy does not supply over 24 volts to the heaters

# Dummy temperature read function
def read_temperature():
    # Replace with real sensor reading
    return float(input("Enter current temperature: "))

#all values are hard coded and needs to be calibrated based on the power supply and resistance heater specs
try:
	while True: 
		temp = read_temperature()
		mv = pid(temp)
		
		resistance = 21.3
		input_voltage = round(((mv * resistance) ** (1/2)) / 36 * (5), 1)
		
		bit_12_input = round( (4095 * input_voltage) / 3.3 )
		
		dac.raw_value = bit_12_input
		
		print('input voltage:', input_voltage) 
		print('dac value:', bit_12_input) 
		print('voltage delivered to heater:', (input_voltage / 5) * 36)
		print('mv value:', mv)

		time.sleep(1)  # sample interval

except KeyboardInterrupt: 
	pass

finally:
	dac.raw_value = 0 




























