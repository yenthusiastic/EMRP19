# Node Firmware

Research for the node firmware is partially based on previous work by EMRP18 project "Smart Cities: Internet of Waste Bins with LoRa" as described in [5. Writing the Embedded Software](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#5-writing-the-embedded-software).

## Programm logic flow

The figure below shows the program logic flow as it is implemented in the node firmaware `garbage_bin__heltech_vl53l0x_ttn.ino`, from first power on/deep sleep wake up until enter deep sleep.
The main function of the programm is to take a distance measurement from the `VL53L0X` sensor, encode it and send the data over the LoRa radio to the next TTN gateway. After every cycle the node goes into deep sleep mode to preserve power. After a predefined amount of time (here 30 seconds) it wakes up again and repeats the cycle.

![Programm Logic Flow](../media/node_firmware_program_logic_flow.jpg)

## Variables to be change
The follwong variables have to be changed for every node.

Integer identifier for the Waste Bin Fill Level Management System, used to identify every node in the user interface and database.
``#define DEVICE_ID``

Each device from the TTN application has its unique **Network Session Key**, **App Session Key** and **Device Address**, they can be found in the `Device Overview` page of each device. 
These values have to be copied into the following variables in the `garbage_bin__heltech_vl53l0x_ttn.ino` code:

 - ``static const u1_t PROGMEM u1_t NWKSKEY[16]``: MSB format
 - ``static const u1_t PROGMEM APPSKEY[16]``: MSB format
 - ``static const u4_t DEVADDR``: MSB format

