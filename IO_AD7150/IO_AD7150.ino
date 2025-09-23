#include <IO_AD7150.h>

IO_AD7150 ad7150;
AD7150_Values result;

void setup()
{
  Serial.begin(9600);
  Wire.begin();

  ad7150.begin();

  ad7150.setOffset(AD7150_OFFSET_AUTO);
  ad7150.setRange(AD7150_RANGE_0_4);

  ad7150.setup();

  //Disable internal pull up on I2C
  //pinMode(A4, INPUT);
  //pinMode(A5, INPUT);

  digitalWrite(A4, LOW);
  digitalWrite(A5, LOW);

  // Print CSV header once
  Serial.println("ADC,CAPDAC,InputRange,Capacitance");
}

void loop()
{
//  // Start a single conversion
  ad7150.configure(AD7150_MODE_SING_CONV);
  delay(20); // Wait for conversion/
//
//  Power down to save energy (optional)
  ad7150.configure(AD7150_MODE_POWER_DOWN);
//
//  Read the values
  result = ad7150.getValue();
//
  // Calculate absolute capacitance (optional)
  float capacitance = (float)(result.value - 12288.0) / 40944.0 * result.inputRange + result.capdac * 12.5/64;
//
//  Print everything
//  Print CSV line: ADC,CAPDAC,InputRange,Capacitance
  Serial.print(result.value);        // ADC
  Serial.print(",");
  Serial.print(result.capdac);       // CAPDAC
  Serial.print(",");
  Serial.print(result.inputRange);   // Input Range
  Serial.print(",");
  Serial.println(capacitance, 5);       // Capacitance

  delay(100);
}
