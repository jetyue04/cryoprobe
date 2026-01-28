import serial
import board

def main():
   
	#Create flowmeter, communicating over the board's default I2C bus
	ser = serial.Serial('/dev/ttyACM0','115200')
	while True:
		flow = ser.readline().decode('utf-8')
		print(flow)
		
if __name__ == '__main__':
	main()

