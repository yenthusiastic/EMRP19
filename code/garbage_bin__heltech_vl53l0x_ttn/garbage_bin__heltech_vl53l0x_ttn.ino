/* Code to measure fill-level of trash bin using distance sensor and send payload to The Things Network gateway, go into sleep mode for 5 minutes and repeat
   Microcontroller used is Heltech WiFi_LoRa_32 (v1)instead of v2
   Original version: https://github.com/emrp/emrp2018_Moers_Trashbins/blob/master/code/embedded%20code/esp32_lorawan_vl53l0x_ttn/esp32_lorawan_vl53l0x_ttn.ino
   Modified by Thu Nguyen 14.01.2020
   Modified by Andreas Markwart 29.02.2020
*/


#include <CayenneLPP.h>
#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>
#include <heltec.h>
#include <Adafruit_VL53L0X.h>
#include <driver/rtc_io.h>

#define uS_TO_S_FACTOR    1000000  // Conversion factor for micro seconds to seconds
#define SLEEP_TIME_IN_SEC 10       // Time ESP32 will go to sleep (in seconds)
#define BUILTIN_LED       25
#define L0X_SHUTDOWN      GPIO_NUM_13
// Schedule TX every this many seconds (might become longer due to duty
// cycle limitations).
const unsigned TX_INTERVAL = 60;
// const unsigned TX_INTERVAL = 1; //OTAA
#define DEVICE_ID         1


RTC_DATA_ATTR uint8_t BootCount = 0;
static bool SleepIsEnabled = false;

Adafruit_VL53L0X lox; // time-of-flight infarred sensor
CayenneLPP lpp(51);

// payload to send to TTN gateway
// static uint8_t payload[3];


// LoRaWAN NwkSKey, network session key
// This is the default Semtech key, which is used by the early prototype TTN
// network.
static const PROGMEM u1_t NWKSKEY[16] = { 0x29, 0xF3, 0xB8, 0xB1, 0x99, 0x91, 0x21, 0x36, 0x6F, 0x93, 0x6D, 0xC0, 0x08, 0x9F, 0xD4, 0xD7 }; //MSB dev4

// LoRaWAN AppSKey, application session key
// This is the default Semtech key, which is used by the early prototype TTN
// network.
static const u1_t PROGMEM APPSKEY[16] = { 0x1C, 0xF3, 0x47, 0xEE, 0x89, 0xD5, 0x57, 0x35, 0x63, 0x07, 0xB3, 0x5F, 0x57, 0xDA, 0x3E, 0xBB }; //MSB dev4

// LoRaWAN end-device address (DevAddr)
static const u4_t DEVADDR = 0x260111EB; // <-- Change this address for every node!
// dev2: 0x26011FA5
// dev3: 0x26011EA6


// uncomment if OTAA is NOT used, comment if it is
void os_getArtEui (u1_t* buf) { }
void os_getDevEui (u1_t* buf) { }
void os_getDevKey (u1_t* buf) { }


static osjob_t sendjob;

// Schedule TX every this many seconds (might become longer due to duty
// cycle limitations),
// uncomment only when sleep is not used

// Pin mapping
const lmic_pinmap lmic_pins = {
  .nss = 18,
  .rxtx = LMIC_UNUSED_PIN,
  .rst = 14,
  .dio = {26, 33, 32},
};


void onEvent (ev_t ev) {
    Serial.print(os_getTime());
    Serial.print(": ");
    switch(ev) {
        case EV_SCAN_TIMEOUT:
            Serial.println(F("EV_SCAN_TIMEOUT"));
            break;
        case EV_BEACON_FOUND:
            Serial.println(F("EV_BEACON_FOUND"));
            break;
        case EV_BEACON_MISSED:
            Serial.println(F("EV_BEACON_MISSED"));
            break;
        case EV_BEACON_TRACKED:
            Serial.println(F("EV_BEACON_TRACKED"));
            break;
        case EV_JOINING:
            Serial.println(F("EV_JOINING"));
            break;
        case EV_JOINED:
            Serial.println(F("EV_JOINED"));
            break;
        case EV_RFU1:
            Serial.println(F("EV_RFU1"));
            break;
        case EV_JOIN_FAILED:
            Serial.println(F("EV_JOIN_FAILED"));
            break;
        case EV_REJOIN_FAILED:
            Serial.println(F("EV_REJOIN_FAILED"));
            break;
        case EV_TXCOMPLETE:
            Serial.println(F("EV_TXCOMPLETE (includes waiting for RX windows)"));
            if (LMIC.txrxFlags & TXRX_ACK)
              Serial.println(F("Received ack"));
            if (LMIC.dataLen) {
              Serial.println(F("Received "));
              Serial.println(LMIC.dataLen);
              Serial.println(F(" bytes of payload"));
            }
            // Schedule next transmission
            os_setTimedCallback(&sendjob, os_getTime()+sec2osticks(TX_INTERVAL), do_send);
// Go to sleep
            goToSleep(); 
            break;
        case EV_LOST_TSYNC:
            Serial.println(F("EV_LOST_TSYNC"));
            break;
        case EV_RESET:
            Serial.println(F("EV_RESET"));
            break;
        case EV_RXCOMPLETE:
            // data received in ping slot
            Serial.println(F("EV_RXCOMPLETE"));
            break;
        case EV_LINK_DEAD:
            Serial.println(F("EV_LINK_DEAD"));
            break;
        case EV_LINK_ALIVE:
            Serial.println(F("EV_LINK_ALIVE"));
            break;
         default:
            Serial.println(F("Unknown event"));
            break;
    }
}


void do_send(osjob_t* j) {
  // Check if there is not a current TX/RX job running
  if (LMIC.opmode & OP_TXRXPEND) {
    Serial.println(F("OP_TXRXPEND, not sending"));
    Heltec.display->drawString(0, 7, "OP_TXRXPEND, not sent");
  } else {
    delay(100);

    // Measure distance
    L0X_init();
    int16_t distance = 0;
    distance = L0X_getDistance();
    L0X_deinit();
    //byte distLow = lowByte(distance);
    //byte distHigh = highByte(distance);
    //payload[0] = distLow;
    //payload[1] = distHigh;
    Serial.print("Distance returned: ");
    Serial.print(distance);

    // Encode using CayenneLPP
    lpp.reset();
    lpp.addDigitalOutput(1, distance);
    lpp.addDigitalOutput(2, DEVICE_ID);

    // Prepare upstream data transmission at the next possible time.
    LMIC_setTxData2(1, lpp.getBuffer(), lpp.getSize(), 0);
    //LMIC_setTxData2(1, payload, sizeof(payload)-1, 0);

    Serial.println(F("Packet queued"));
    Heltec.display->clear();
    Heltec.display->drawString(0, 7, "PACKET QUEUED");
    Heltec.display->display();
  }
  // Next TX is scheduled after TX_COMPLETE event.
}



void L0X_init(void)
{
  rtc_gpio_hold_dis(L0X_SHUTDOWN);
  pinMode(L0X_SHUTDOWN, OUTPUT);
  digitalWrite(L0X_SHUTDOWN, HIGH);

  delay(100);
  //Wire.begin(21, 22, 100000);
  if (!lox.begin()) {
    Serial.println(F("Failed to boot VL53L0X"));
    while (1);
  }
}


void L0X_deinit(void)
{
  digitalWrite(L0X_SHUTDOWN, LOW);
}


// return distance in cm
//int16_t L0X_getDistance(void)
int8_t L0X_getDistance(void)
{
  VL53L0X_RangingMeasurementData_t measure;
  int16_t distance = 0;
  for (int i = 0; i < 5; i++)
  {
    delay(100);
    Serial.print("Reading a measurement... ");
    lox.rangingTest(&measure, false); // pass in 'true' to get debug data printout!

    if (measure.RangeStatus != 4) {  // phase failures have incorrect data
      distance += measure.RangeMilliMeter / 10;
      Serial.print("Distance (cm): "); Serial.println(measure.RangeMilliMeter / 10);
    } else {
      Serial.println(" out of range ");
      return 0;
    }
  }
  Serial.print("Returning Distance: ");
  Serial.println((int)distance/5);
  return ((int)(distance / 5));
}

//
void turnOffPeripherals(void)
{
  Serial.println("Going to sleep, shutting down peripherals...");
  delay(100);
  Serial.end();
  rtc_gpio_hold_en(L0X_SHUTDOWN);
  Heltec.display->sleep();
  LoRa.sleep();
}

void goToSleep(void)
{
  SleepIsEnabled = true;
  // Sleep all peripherals and enable RTC timer
  turnOffPeripherals();
  //esp_sleep_enable_timer_wakeup(SLEEP_TIME_IN_SEC * uS_TO_S_FACTOR);
  //esp_light_sleep_start();
  Serial.println("Going into deepsleep!");
  esp_sleep_enable_timer_wakeup(SLEEP_TIME_IN_SEC * uS_TO_S_FACTOR);
  esp_deep_sleep_start();

  // After timer runs out
  Serial.begin(115200);           // uncomment this for debugging
  Serial.println("after sleep");  // uncomment this for debugging
  SleepIsEnabled = false;
}




void setup() {
  Heltec.begin(true /*DisplayEnable Enable*/, true /*LoRa Enable*/, true /*Serial Enable*/, true, 866E6);
  Heltec.LoRa.setSpreadingFactor(7);
  Serial.begin(115200);
  
  Serial.println("=============================================");
  if (BootCount == 0)
  {
    Serial.println("First Boot");
    Serial.println("=============================================");
  }
  else
  {
    Serial.println("Woke up");
    Serial.println("=============================================");
  }

  Serial.print("BootCount: "); Serial.println(BootCount);
  BootCount++;

  // LMIC init
  os_init();

  // Reset the MAC state. Session and pending data transfers will be discarded.
  LMIC_reset();

  // Set static session parameters. Instead of dynamically establishing a session
  // by joining the network, precomputed session parameters are be provided.
  #ifdef PROGMEM
  // On AVR, these values are stored in flash and only copied to RAM
  // once. Copy them to a temporary buffer here, LMIC_setSession will
  // copy them into a buffer of its own again.
  uint8_t appskey[sizeof(APPSKEY)];
  uint8_t nwkskey[sizeof(NWKSKEY)];
  memcpy_P(appskey, APPSKEY, sizeof(APPSKEY));
  memcpy_P(nwkskey, NWKSKEY, sizeof(NWKSKEY));
  LMIC_setSession (0x1, DEVADDR, nwkskey, appskey);
  #else
  // If not running an AVR with PROGMEM, just use the arrays directly
  LMIC_setSession (0x1, DEVADDR, NWKSKEY, APPSKEY);
  #endif

  #if defined(CFG_eu868)
  // Set up the channels used by the Things Network, which corresponds
  // to the defaults of most gateways. Without this, only three base
  // channels from the LoRaWAN specification are used, which certainly
  // works, so it is good for debugging, but can overload those
  // frequencies, so be sure to configure the full frequency range of
  // your network here (unless your network autoconfigures them).
  // Setting up channels should happen after LMIC_setSession, as that
  // configures the minimal channel set.
  // NA-US channels 0-71 are configured automatically
  LMIC_setupChannel(0, 868100000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(1, 868300000, DR_RANGE_MAP(DR_SF12, DR_SF7B), BAND_CENTI);      // g-band
  LMIC_setupChannel(2, 868500000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(3, 867100000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(4, 867300000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(5, 867500000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(6, 867700000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(7, 867900000, DR_RANGE_MAP(DR_SF12, DR_SF7),  BAND_CENTI);      // g-band
  LMIC_setupChannel(8, 868800000, DR_RANGE_MAP(DR_FSK,  DR_FSK),  BAND_MILLI);      // g2-band
  // TTN defines an additional channel at 869.525Mhz using SF9 for class B
  // devices' ping slots. LMIC does not have an easy way to define set this
  // frequency and support for class B is spotty and untested, so this
  // frequency is not configured here.
  #elif defined(CFG_eu868)
  // NA-US channels 0-71 are configured automatically
  // but only one group of 8 should (a subband) should be active
  // TTN recommends the second sub band, 1 in a zero based count.
  // https://github.com/TheThingsNetwork/gateway-conf/blob/master/US-global_conf.json
  LMIC_selectSubBand(1);
  #endif


  // Disable link check validation
  LMIC_setLinkCheckMode(0);

  // TTN uses SF9 for its RX2 window.
  LMIC.dn2Dr = DR_SF9;

  // Set data rate and transmit power for uplink (note: txpow seems to be ignored by the library)
  LMIC_setDrTxpow(DR_SF7, 14);

  // Start job (using ABP)
  do_send(&sendjob);
}

void loop() {
 //*

  if (!SleepIsEnabled) // Enable peripherals again (after each sleep)
  {
   // DisplayEnable Enable, LoRa Enable, Serial Enable, 866E6
    //Heltec.begin(true , true , true , true, 866E6);   
    
    //Serial.println("Enabling sleep inside loop");
    //Heltec.LoRa.setSpreadingFactor(7);

    SleepIsEnabled = true;
  }
 //*/
  os_runloop_once();
}
