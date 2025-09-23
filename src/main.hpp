#include <Arduino.h>

// Imports
#include <iostream>
#include <math.h>    
#include <vector>
#include <string>
#include <stdexcept>

#include <sys/time.h>
#include <time.h>


#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "ble_console.hpp"
#include "esp_light.hpp"


// Constants
#define MIC_PIN       16
#define SPEAKER_PIN   18
#define RED_PIN       5
#define GREEN_PIN     6
#define BLUE_PIN      4

#define SERVICE_UUID        "4c3c2810-045d-4880-a1b2-e9143e397613"
#define CHARACTERISTIC_UUID "005e1887-1150-43e5-a985-b1b741437ea6"
#define CONSOLE_UUID        "311b1fd7-7411-4d89-afcc-0fb165f4aac8"

namespace Lamp {
    // Global variables/arrays
    BLELogger ble_logger = NULL;
    BLEServer* p_bleserver = NULL;
    BLECharacteristic* p_ble_char = NULL;
    BLECharacteristic* p_ble_console = NULL;
    bool device_connected = false;
    bool old_device_connected = false;
    int value = -1;
    uint32_t loop_count = 0;

    void set_time_comp_time();
    void update_audio();
    void setup_BLE();
    void main_loop();
}

void loop();
void setup();

