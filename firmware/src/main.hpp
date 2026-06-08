#include <Arduino.h>

#include <iostream>
#include <math.h>
#include <vector>
#include <string>

#include <sys/time.h>
#include <time.h>
#include <EEPROM.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "ble_console.hpp"
#include "esp_light.hpp"

// Pin assignments
#define MIC_PIN     16
#define SPEAKER_PIN 18
#define RED_PIN     5
#define GREEN_PIN   6
#define BLUE_PIN    4

// BLE UUIDs
#define SERVICE_UUID        "4c3c2810-045d-4880-a1b2-e9143e397613"
#define CHARACTERISTIC_UUID "005e1887-1150-43e5-a985-b1b741437ea6"
#define CONSOLE_UUID        "311b1fd7-7411-4d89-afcc-0fb165f4aac8"

// EEPROM layout: bytes [0 .. BUTTONS*3-1] = rgb_mapping, addr 200 = mode, addr 201 = bpm
#define EEPROM_SIZE  256
#define BUTTONS      53   // 48 notes + 5 special: metronome, normal, fade1/2/3
#define FLASH_DELAY  2    // ms per brightness step inside light.flash()
#define FADE_STEP_MS 10   // ms per colour step in fade mode (100 steps = 1 s cycle)

namespace Lamp {
    BLELogger ble_logger = NULL;
    BLEServer* p_bleserver = NULL;
    BLECharacteristic* p_ble_char = NULL;
    BLECharacteristic* p_ble_console = NULL;

    bool device_connected = false;
    bool old_device_connected = false;
    uint32_t loop_count = 0;

    // Shared state written by BLE callback (BLE task) and read by main_loop.
    // uint8_t / float writes are atomic on Xtensa; rgb_mapping is only modified
    // by BLE callback after setup() completes, so no mid-init races.
    uint8_t current_mode = 2;       // 0=Metronome, 1=Note Match, 2=Normal, 3=Fade
    float   bpm = 90.0f;
    std::vector<RGB> rgb_mapping;   // 53 entries; loaded from EEPROM in setup()
    bool eeprom_dirty = false;      // flag: commit EEPROM in main_loop, not in callback

    std::time_t start_time;
    bool audio_update_loop = true;

    void set_time_comp_time();
    void load_from_eeprom();
    void update_audio(void* pvParameters);
    void setup_BLE();
    void main_loop();
}

void loop();
void setup();
