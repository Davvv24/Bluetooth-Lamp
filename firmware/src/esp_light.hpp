#pragma once

#include <Arduino.h>
#include <vector>

// RGB colour array structure
struct RGB {float r, g, b;};

RGB lerp(const RGB& a, const RGB& b, float t);

// Produces a smooth cycle through three colours in `steps` evenly-spaced steps.
std::vector<RGB> generate_fade(const RGB& c1, const RGB& c2, const RGB& c3, int steps);

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
    