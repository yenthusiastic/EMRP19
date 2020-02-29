# Node Firmware

## Programm logic flow

The figure below shows the program logic flow as it is implemented in the file `garbage_bin__heltech_vl53l0x_ttn.ino`, from first power on/deep sleep wake up until enter deep sleep.
The main function of the programm is to take a distance measurement from the `VL53L0X` sensor, encode it and send the data over the LoRa radio to the next TTN gateway. After every cycle the node goes into deep sleep mode to preserve power. After a predefined amount of time (here 30 seconds) it wakes up again and repeats the cycle.

![Programm Logic Flow](../media/node_firmware_program_logic_flow.jpg)
