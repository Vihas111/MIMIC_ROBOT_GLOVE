# MARS Project — Wiring Guide

## Components

| Qty | Component              | Notes                            |
|-----|------------------------|----------------------------------|
| 1   | Arduino Uno            |                                  |
| 5   | Flex sensors           | One per finger                   |
| 5   | 10 kOhm resistors      | One per flex sensor (pull-down)  |
| 1   | USB cable (A-to-B)     | Arduino to laptop                |
|     | Jumper wires, breadboard |                                |

## Pin Assignment Summary

```
 Arduino Uno Pin │ Connected To
─────────────────┼──────────────────────────────
  A0             │ Thumb  flex sensor voltage divider output
  A1             │ Index  flex sensor voltage divider output
  A2             │ Middle flex sensor voltage divider output
  A3             │ Ring   flex sensor voltage divider output
  A4             │ Pinky  flex sensor voltage divider output
  5V             │ flex sensor power rail
  GND            │ resistor ground rail
```

**Why software I2C?**  On the Uno, pins A4/A5 double as the hardware
I2C bus (SDA/SCL).  Since we need all five analog pins for flex sensors,
the firmware bit-bangs I2C on digital pins D2/D3 instead, leaving
A0–A4 free.  Because we never call `Wire.begin()`, A4 remains a
normal analog input.


## Flex Sensor Wiring (repeat x5)

Each flex sensor forms a **voltage divider** with a 10 kOhm pull-down
resistor.  The analog pin reads the mid-point voltage, which changes
as the sensor bends.

```
            Flex Sensor (variable R)
  5V ────────┤                       ├──── junction ──── Analog Pin (A0–A4)
                                              │
                                          [10 kOhm]
                                              │
                                            GND
```

### Step-by-step (per sensor)

1. Connect one leg of the flex sensor to the **5 V rail**.
2. Connect the other leg to:
   - The **analog input pin** (A0 for thumb, A1 for index, etc.)
   - One leg of a **10 kOhm resistor**
3. Connect the other leg of the 10 kOhm resistor to **GND**.

### How it works

- **Flat** (no bend): Flex resistance ~ 25 kOhm → V_out ≈ 1.4 V → ADC ≈ 290
- **Bent 90 deg**: Flex resistance ~ 100 kOhm → V_out ≈ 0.45 V → ADC ≈ 92
- Higher bend → higher flex resistance → lower voltage → lower ADC value


## Complete Breadboard Layout

```
 +5V RAIL ═══════════════════════════════════════════════════════

  ┌─Flex(thumb)──┐  ┌─Flex(index)──┐  ┌─Flex(middle)─┐  ┌─Flex(ring)──┐  ┌─Flex(pinky)──┐
  │              │  │              │  │              │  │             │  │              │
 5V            ──┤ 5V           ──┤ 5V           ──┤ 5V          ──┤ 5V           ──┤
               A0│              A1│              A2│             A3│              A4│
            10kΩ │           10kΩ │           10kΩ │          10kΩ │           10kΩ │
              GND│             GND│             GND│            GND│             GND│

  

 GND RAIL ═══════════════════════════════════════════════════════
```


## Glove Assembly Tips

1. **Solder leads** to each flex sensor — they break easily at the
   crimp if you just push wires on.
2. **Run wires along the back of the glove** (not the palm) so they
   don't interfere with bending.
3. **Secure with hot glue or Velcro** — avoid adhesive tape on the
   flex sensors themselves.
4. **Use a ribbon cable or braided wire** from the glove to the
   breadboard/Arduino to keep things tidy.


## Calibration

After uploading the Arduino sketch, open the Serial Monitor at
**115200 baud** and check the output:

```
thumb,index,middle,ring,pinky
```

1. **Flex sensors**: Note the ADC values with hand flat and fully
   clenched.  Update the calibration parameters in the ROS 2 launch:
   ```
   ros2 launch mars_hand display.launch.py thumb_flat:=110 thumb_bent:=20 ...
   ```


