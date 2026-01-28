import serial
import time
from PID import PID  # assuming your PID class from IvPID.py

# Open serial to Arduino (Programming port)
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)

# PID setup
setpoint = -110  # target temperature
pid = PID(P=0.2, I=0.01, D=0.05)
pid.SetPoint = setpoint
pid.setSampleTime(1)  # 1 second update

# Dummy temperature read function
def read_temperature():
    # Replace with real sensor reading
    return float(input("Enter current temperature: "))

while True:
    temp = read_temperature()
    pid.update(temp)
    mv = pid.output  # This is the PID manipulated variable

    # Map MV to voltage (0–3.3 V)
    # Optionally clip if PID output can exceed range
    voltage = max(0.0, min(3.3, mv))

    # Send to Arduino
    arduino.write(f"{voltage}\n".encode())

    # Read Arduino feedback
    response = arduino.readline().decode().strip()
    if response:
        print(f"Arduino: {response}, MV: {mv:.3f}, voltage: {voltage:.3f}")

    time.sleep(1)  # sample interval
