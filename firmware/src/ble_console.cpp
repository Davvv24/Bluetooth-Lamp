#include "ble_console.hpp"

BLELogger::BLELogger(BLECharacteristic* p_ble_console) {
    this->start_time = std::time(0);   // get time now
    this->p_ble_console_char = p_ble_console;
}

void BLELogger::log(const char* message) {
    std::string temp = std::string(message); // Convert the message to a string
    std::time_t t = std::time(0);   // get time now
    std::tm* now = std::localtime(&t); // Get the current time
    std::string time_str = "\t[" + std::to_string(now->tm_hour) + ":" + std::to_string(now->tm_min) + ":" + std::to_string(now->tm_sec) + "]\t";
    temp =  time_str + temp;
    this->p_ble_console_char->setValue(temp); // Set the value of the characteristic to the message
    this->p_ble_console_char->notify();
}

void BLELogger::log(const String& message) {
    this->p_ble_console_char->setValue(message.c_str()); // Set the value of the characteristic to the message
    this->p_ble_console_char->notify();
}