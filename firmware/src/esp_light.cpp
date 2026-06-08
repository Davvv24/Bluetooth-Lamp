#include "esp_light.hpp"

RGB lerp(const RGB& a, const RGB& b, float t) {
    return {a.r + (b.r - a.r) * t, a.g + (b.g - a.g) * t, a.b + (b.b - a.b) * t};
}

std::vector<RGB> generate_fade(const RGB& c1, const RGB& c2, const RGB& c3, int steps) {
    std::vector<RGB> out;
    out.reserve(steps);
    for (int i = 0; i < steps; i++) {
        float t = float(i) / (steps - 1);
        if      (t < 0.33f) out.push_back(lerp(c1, c2, t / 0.33f));
        else if (t < 0.66f) out.push_back(lerp(c2, c3, (t - 0.33f) / 0.33f));
        else                out.push_back(lerp(c3, c1, (t - 0.66f) / 0.34f));
    }
    return out;
}

ESPLight::ESPLight(uint8_t red_pin, uint8_t green_pin, uint8_t blue_pin, bool esp_light){
  this->red_pin = red_pin;
  this->green_pin = green_pin;
  this->blue_pin = blue_pin;
  this->esp_light = true;
  // Configure pinmode
  pinMode(red_pin, OUTPUT);
  pinMode(green_pin, OUTPUT);
  pinMode(blue_pin, OUTPUT);
}
  

void ESPLight::set(uint8_t red_val, uint8_t green_val, uint8_t blue_val){
  // Set light colour
  analogWrite(red_pin, red_val);
  analogWrite(green_pin, green_val);
  analogWrite(blue_pin, blue_val);
  neopixelWrite(RGB_BUILTIN,red_val,green_val,blue_val);
}

void ESPLight::set(const RGB& colour){
  // Set light colour
  uint8_t red_val = (uint8_t)(colour.r*255);
  uint8_t green_val = (uint8_t)(colour.g*255);
  uint8_t blue_val = (uint8_t)(colour.b*255);
  ESPLight::set(red_val, green_val, blue_val);
}

// Overloaded flash method
void ESPLight::flash(uint8_t red_val, uint8_t green_val, uint8_t blue_val, uint8_t time_delay){
// Iteratively fade down the RGB values over a time period
  for(int i=256; i>0; i=i-2){
    this->set(red_val, green_val, blue_val);
    // Set light colour
    if(red_val>0){red_val-=2;}
    if(green_val>0){green_val-=2;}
    if(blue_val>0){blue_val-=2;}
    // Wait
    delay(time_delay*3);
  }
}
// Overloaded flash method
void ESPLight::flash(const RGB& colour,  uint8_t time_delay){
  uint8_t red_val = (uint8_t)(colour.r*255);
  uint8_t green_val = (uint8_t)(colour.g*255);
  uint8_t blue_val = (uint8_t)(colour.b*255);

  // Iteratively fade down the RGB values over a time period
  for(int i=256; i>0; i=i-2){
    this->set(red_val, green_val, blue_val);
    // Set light colour
    if(red_val>0){red_val-=2;}
    if(green_val>0){green_val-=2;}
    if(blue_val>0){blue_val-=2;}
    // Wait
    delay(time_delay*3);
  }
}