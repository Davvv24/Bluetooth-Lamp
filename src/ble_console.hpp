#pragma once

#include <Arduino.h>

#include <BLEDevice.h>
#include <BLEServer.h>

#include <iostream>
#include <string>
#include <ctime>   


class BLELogger {
private:
    std::time_t start_time;   
    BLECharacteristic* p_ble_console_char = NULL;
public:
    BLELogger(BLECharacteristic* p_ble_console);
    void log(const char* message);
    void log(const String& message);
};