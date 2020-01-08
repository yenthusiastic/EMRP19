A summary of steps to set up the hardware needed for monitoring the fill level of the trash bin and send the data to The Things Network.
Is based on previous work by EMRP18 project _"Smart Cities: Internet of Waste Bins with LoRa"_ as described in [this documentation](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md).
The following document will only summarize the steps taken and highlight **(in bold)** the modifications made compared to the previous work, for details please refer to the linked documentation above.

#### 1. Prepare hardware
- Required components:
    - Heltec WiFi_LoRa_32 ESP32-based module with 868MHz antenna (V1)
    - [Adafruit VL6180X](https://www.adafruit.com/product/3316) Time-of-flight distance sensor breakout board
- Pin headers have to be soldered to both modules
. Connect the antenna to the Heltec WiFi_LoRa_32 module before powering it with 5V over mciroUSB cable.

#### 2. Set up Arduino IDE
- [Install Arduino IDE](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#2-software-installation)
- Within Arduino IDE:
    - Add board definitions for the `Heltec WiFi_LoRa_32` module **using instructions from [Heltec documentation](https://docs.heltec.cn/#/en/user_manual/how_to_install_esp32_Arduino)**. The method described in EMRP18 project did not work for this module (V1).
    - Use Arduino IDE Library Manager to install required libraries by clicking on `Tools -> Manage Libraries...` and search for the name of the library:
        -  Install `Heltec ESP32 Dev-Boards` library by `Heltec Automation` **using Arduino Library Manager instead of the ZIP-library**.

        ![heltec_lib](../media/heltec-lib.PNG)

        - Install `Adafruit VL6180X` library by `Adafruit`
        - Install `MCCI LoRaWAN LMIC` library by `IBM, Mathis Koojiman, Terry Moore, ChaeHee Won, Frank Rose`
        - `CayeneLPP` library **was not installed due to incompatibility** with V1 module

#### Hardware Connections
- Although different hardware modules (Heltec WiFi_LoRa_ESP32 V1 & VL6180X) are used, the wiring between the 2 modules are the same, which is summarized in the following table:

Heltec WiFi_LoRa_ESP32 V1 Pin | VL6180X Breakout board Pin 
---------|----------
 3V3 | Vin 
 GND | GND 
 15 (SCL) | SCL
 4 (SDA) | SDA
 13 | XSHUT 

The pin-out diagram of the Heltec WiFi_LoRa_ESP32 V1 is available [here](https://github.com/Heltec-Aaron-Lee/WiFi_Kit_series/blob/master/PinoutDiagram/WIFI_LoRa_32_V1.pdf). 

#### Set up The Things Network Console
- [Add a new application](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#41-setting-up-a-new-ttn-application)
- [Register a new device with OTAA Activation method](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#43-registering-a-device)

#### Upload code to ESP32 module
- Download the code from [here](code/heltec_vl6180_ttn/heltec_vl6180_ttn.ino).
- [Edit the LMIC config file](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#514-editing-the-lmic-config-file).
- [Copy the device keys from TTN Console to the code.](https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/documentation/from_sensor_to_ttn.md#512-device-keys)
- Under `Tools -> Board` choose **WiFi LoRa 32** from `Heltec ESP32 Arduino`

![board-select](../media/board.png)

- Connect the board to PC, under `Tools -> Port` select the correct port
- Upload the code

#### Verify data received by TTN gateway
