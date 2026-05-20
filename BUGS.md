# Known Bugs — temperature_pid_control.py

Issues identified in `temperature-control/temperature_pid_control.py`, the active temperature control script.

---

## BUG 1: `round()` collapses DAC output to 4 discrete levels

**File:** `temperature-control/temperature_pid_control.py`, line 180

**Code:**
```python
input_voltage = round(mv / Vmax * 5)
```

**What it does:**
`pid.output_limits = (0, 22.5)` and `Vmax = 36`, so `mv / Vmax * 5` ranges from 0 to 3.125. Rounding that to the nearest integer produces only four possible values: 0, 1, 2, or 3. The MCP4725 DAC then outputs one of four fixed voltages, and the heater receives one of four fixed power levels (~0V, 7.2V, 14.4V, 21.6V).

**Why it's a problem:**
The PID is computing a continuous proportional signal, but `round()` throws away all the precision. The result is bang-bang control with 4 steps instead of the 4096-step proportional control the DAC is capable of. The heater cannot fine-tune — it can only jump between large discrete power levels.

**Why the temperature changes level on restart:**
The PID integral accumulates differently every run depending on the initial temperature and cooldown rate. At steady state the PID settles on a slightly different continuous output value each time. A small run-to-run difference in the settled PID output is enough to cross the rounding boundary between, say, 1V and 2V — a jump of 7.2V at the heater — so the system locks onto a different discrete power level and the temperature stabilizes noticeably higher or lower.

**Fix:**
Remove the `round()` on `input_voltage`. Only round the final integer DAC value:
```python
input_voltage = mv / Vmax * 5                                  # keep floating point
bit_12_input = round(min((4095 * input_voltage) / 3.3, 4095))  # round here only
dac.raw_value = bit_12_input
```

---

## BUG 2: Fault register never checked

**File:** `temperature-control/temperature_pid_control.py`, after each `_wait_for_oneshot()` call

**Code:**
```python
ColdHead._wait_for_oneshot()
temp_coldhead = calibrated_temps(ColdHead.unpack_temperature(), 'ColdHead')
# same pattern for HeatExF, HeatExB, Chamber
```

**What it does:**
The MAX31856 has a fault status register that flags hardware problems: open thermocouple circuit, short to GND or VCC, out-of-range cold junction, and input over/under voltage. When any of these conditions are active, the temperature register contains invalid data. The code never reads this register, so fault conditions are silently accepted as valid temperatures.

**Why it's a problem:**
An intermittent thermocouple connection (loose wire, cold-temperature contraction at connectors) will cause random large spikes or implausible readings with no indication of why. The bad value goes directly into the PID and into the log.

**Fix:**
Check `sensor.fault` after each read. The Adafruit library returns a dict of fault flags:
```python
ColdHead._wait_for_oneshot()
fault = ColdHead.fault
if any(fault.values()):
    print(f"ColdHead fault: {fault}")
    # skip this reading or handle appropriately
else:
    temp_coldhead = calibrated_temps(ColdHead.unpack_temperature(), 'ColdHead')
```

---

## BUG 3: ColdHead has no calibration applied

**File:** `temperature-control/temperature_pid_control.py`, `calibrated_temps()` function

**Code:**
```python
elif TC == 'ColdHead':
    ActualTemp = temp   # raw value returned unchanged
```

**What it does:**
HeatExF, HeatExB, and Chamber all have empirical linear corrections applied to account for thermocouple offsets and cable errors. ColdHead returns the raw MAX31856 reading with no correction.

**Why it's a problem:**
If the ColdHead thermocouple has any systematic offset (which all thermocouples do to some degree, especially at cryogenic temperatures), that error is permanently baked into the logged data and into the PID if ColdHead is ever used as the control sensor. The other sensors were calibrated against a reference; ColdHead was not, or the calibration was lost.

**Action needed:**
Run ColdHead against a calibrated reference sensor at a known temperature and derive a correction, or confirm that no correction is intentional and document why.

---

## BUG 4: Thermocouple type mismatch risk

**File:** `temperature-control/temperature_pid_control.py`, sensor initialization

**Code:**
```python
ColdHead = adafruit_max31856.MAX31856(spi, cs13, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
HeatExF  = adafruit_max31856.MAX31856(spi, cs16, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
HeatExB  = adafruit_max31856.MAX31856(spi, cs25, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
Chamber  = adafruit_max31856.MAX31856(spi, cs26, thermocouple_type=adafruit_max31856.ThermocoupleType.T)
```

**What it does:**
The MAX31856 uses the thermocouple type setting to select a polynomial for converting the measured microvolt signal to a temperature. All four sensors are hardcoded as T-type.

**Why it's a problem:**
T-type and K-type thermocouples use the same connector and look identical. If any of the installed thermocouples are K-type (or any other type), the chip applies the wrong conversion polynomial. The error is not constant — it grows with temperature difference from the cold junction and can reach tens of degrees at cryogenic temperatures. This would show up as a systematic offset that does not match any of the linear calibration corrections.

**How to check:**
Verify the physical thermocouple markings or datasheet. T-type uses copper (+) and constantan (−) wires; K-type uses chromel (+) and alumel (−). The insulation color coding also differs (T-type: blue/red in US convention, K-type: yellow/red).

---

## BUG 5: Cold junction offset not verified

**File:** `temperature-control/temperature_pid_control.py`, sensor initialization

**What it does:**
The MAX31856 performs cold junction compensation (CJC) automatically using an internal thermistor that measures the chip's own temperature. It adds this measured CJ temperature to the thermocouple contribution to give an absolute temperature reading.

**Why it's a problem:**
If the chip is not at a well-known, stable temperature — for example, if it sits near a heater, in a draft, or in a poorly ventilated enclosure — the internal CJC reading drifts and every sensor reading drifts with it by the same amount. A chip sitting at 20°C ambient that experiences a 5°C thermal drift introduces a 5°C shift in all four temperature channels simultaneously. The MAX31856 also has a cold junction offset register (`CJTO`) that can correct for a systematic CJC error; the code never sets this register, so it is left at its power-on default of zero.

**How to check:**
Place all four sensors at room temperature with no temperature gradient. All four readings should agree with a thermometer to within ~3°C (the MAX31856's rated CJC accuracy). A systematic offset across all sensors pointing to the same value suggests CJC is the source.
