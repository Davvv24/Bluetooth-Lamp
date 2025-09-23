#pragma once

#include <Arduino.h>

// RGB colour array structure
struct RGB {float r, g, b;};
// lerp function of RGB structure between two colours a and b (rgb values treated as vectors)
RGB lerp(const RGB& a, const RGB& b, float t);


class ESPLight {
private:
    int red_pin, green_pin, blue_pin;
    bool esp_light;

public:
    // Constructor
    ESPLight(uint8_t red_pin, uint8_t green_pin, uint8_t blue_pin, bool esp_light);

    void set(uint8_t red_val, uint8_t green_val, uint8_t blue_val);
    void set(const RGB& colour);

    // Method to flash the light
    void flash(uint8_t red_val, uint8_t green_val, uint8_t blue_val, uint8_t time_delay);
    void flash(const RGB& colour, uint8_t time_delay);
};
    