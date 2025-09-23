#include "IO_AD7150.h"
IO_AD7150::IO_AD7150(uint8_t i2cAddress)
{
   m_i2cAddress = i2cAddress;
   m_offset = AD7150_OFFSET_DAC_4;
   m_range = AD7150_RANGE_0_4;
}

/**************************************************************************/
/*!
    @brief  Sets up the HW (reads coefficients values, etc.)
*/
/**************************************************************************/
void IO_AD7150::begin()
{
  Wire.begin();

 
}

void IO_AD7150::writeRegister(uint8_t reg, uint16_t value)
{
  Wire.begin();
  Wire.beginTransmission(m_i2cAddress);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
  delay(4); //Wait a little bit that the change is effective
 
  digitalWrite(A4, LOW);
  digitalWrite(A5, LOW);
}

void IO_AD7150::setup()
{
  writeRegister(AD7150_REG_CH1_SENSITIVITY, 0x08);
  writeRegister(AD7150_REG_CH1_SETUP, m_range);
  writeRegister(AD7150_REG_CONFIGURATION, 0x12);    //Conversion enabled on ch1 and ch2, Single Conversion mode
  writeRegister(AD7150_REG_POWER_DOWN_TIMER, 0x00);
  writeRegister(AD7150_REG_CH1_CAPDAC, m_offset);
}

void IO_AD7150::configure(AD7150_adMode_t mode)
{
  writeRegister(AD7150_REG_CONFIGURATION, mode);

}

void IO_AD7150::setOffset(AD7150_adOffset_t offset)
{
  m_offset = offset;
}
void IO_AD7150::setRange(AD7150_adRange_t range)
{
  m_range = range;
}

AD7150_Values IO_AD7150::getValue(void)
{
  uint8_t data[3];

  // set register pointer
  Wire.beginTransmission(AD7150_I2C_ADDRESS);
  Wire.write(0);
  Wire.endTransmission(false);


  Wire.requestFrom(AD7150_I2C_ADDRESS, 3, true);  
  for (int i = 0; Wire.available(); i++)
  {
    data[i] = Wire.read();
  }

  uint16_t val = data[2] | data[1] << 8;
  uint8_t status = data[0];

  // read CAPDAC

  // set register pointer
  Wire.beginTransmission(AD7150_I2C_ADDRESS);
  Wire.write(AD7150_REG_CH1_CAPDAC);
  Wire.endTransmission(false);

  Wire.requestFrom(AD7150_I2C_ADDRESS, 1, true);
  for (int i = 0; Wire.available(); i++)
  {
    data[i] = Wire.read();
  }
  uint8_t capdac = data[0] & 0x3f;

  //read input range
  Wire.beginTransmission(AD7150_I2C_ADDRESS);
  Wire.write(AD7150_REG_CH1_SETUP);
  Wire.endTransmission(false);

  Wire.requestFrom(AD7150_I2C_ADDRESS, 1, true);
  for (int i = 0; Wire.available(); i++)
  {
    data[i] = Wire.read();
  }
  uint8_t range = data[0];

  bool range_H = (range & 0x80) >> 7; // 0x80 = 1000 0000
  bool range_L = (range & 0x40) >> 6; // 0x40 = 0100 0000

  // Combine bits into a 2-bit index
  uint8_t index = (range_H << 1) | range_L;

  float inputRangePF;
  // float capdacStep;

  // Use a switch to map the 2-bit value
  switch (index) {
      case 0b00:
          inputRangePF = 2.0;
          // capdacStep = 4;
          break;
      case 0b01:
          inputRangePF = 0.5;
          // capdacStep = 1;
          break;
      case 0b10:
          inputRangePF = 1.0;
          // capdacStep = 2;
          break;
      case 0b11:
          inputRangePF = 4.0;
          // capdacStep = 8;
          break;
  }

  AD7150_Values result;
  result.status = status;
  result.value = val;
  result.capdac = capdac;
  result.inputRange = inputRangePF;

  return result;
}
