#include "main.hpp"

namespace Lamp{
  // Global variables/arrays
  ESPLight light = ESPLight((uint8_t)RED_PIN, (uint8_t)GREEN_PIN, (uint8_t)BLUE_PIN, true);
  
  std::time_t start_time;   
  bool audio_update_loop = true; 

  // Callback class that calls onConnect when connected and onDisconnect when disconnected
  class BLE_Server_Callback: public BLEServerCallbacks {
    // When a connect callback is called, set the connection status to true and flash to indicate a successful connection
    void onConnect(BLEServer* p_bleserver) {
      device_connected = true;
      light.flash(0,127,0,2);
    };
    // When a connection lost callback is called, set the connection status to false and flash to indicate a lost connection
    void onDisconnect(BLEServer* p_bleserver) {
      device_connected = false;
      light.flash(127,0,0,2);
    }
  };
  // Callback class that triggers whenever the characteristic is written to
  class BLE_Char_Callback: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* p_ble_char) {
      // Read 16-bit value as a string and cast to integer
      std::string value = p_ble_char->getValue();
      // Check command is non-zero
      if (value.length() > 0) {
        light.flash(0,0,127,2);
      }
    }
  };

  class BLE_Console_Callback: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* p_ble_char) {
      // Read 16-bit value as a string and cast to integer
      std::string value = p_ble_char->getValue();
      // Check command is non-zero
      if (value.length() > 0) {
        light.flash(0,0,127,2);
      }
    }
  };


  // Sets starting time to compile time
  void set_time_comp_time() {
    // Parse __DATE__ and __TIME__ macros into components
    struct tm compile_time = {0};
    strptime(__DATE__, "%b %d %Y", &compile_time);  // Parse date (e.g., "Apr 7 2025")
    strptime(__TIME__, "%H:%M:%S", &compile_time); // Parse time (e.g., "16:43:00")

    // Convert compile_time to time_t
    time_t t = mktime(&compile_time);

    // Set system time
    struct timeval now = {.tv_sec = t};
    settimeofday(&now, NULL);

    printf("ESP32 time set to compile date: %s\n", asctime(&compile_time));
  }
    
  void setup_BLE(){
    // Create the BLE Device
    BLEDevice::init("ESP32");

    // Create the BLE Server
    p_bleserver = BLEDevice::createServer();
    p_bleserver->setCallbacks(new BLE_Server_Callback());
    // Create the BLE Service
    BLEService *p_ble_service = p_bleserver->createService(SERVICE_UUID);
    
    // Create a BLE Characteristic
    p_ble_char = p_ble_service->createCharacteristic(
                        CHARACTERISTIC_UUID,
                        BLECharacteristic::PROPERTY_READ   |
                        BLECharacteristic::PROPERTY_WRITE  |
                        BLECharacteristic::PROPERTY_NOTIFY |
                        BLECharacteristic::PROPERTY_INDICATE
                      );

    // Set callbacks values being written to 
    p_ble_char->setCallbacks(new BLE_Char_Callback());
    // Create a default BLE Descriptor
    p_ble_char->addDescriptor(new BLE2902());

    p_ble_console = p_ble_service->createCharacteristic(
      CONSOLE_UUID,
      BLECharacteristic::PROPERTY_READ   |
      BLECharacteristic::PROPERTY_WRITE  |
      BLECharacteristic::PROPERTY_NOTIFY |
      BLECharacteristic::PROPERTY_INDICATE
    );
    // Set callbacks values being written to 
    p_ble_console->setCallbacks(new BLE_Console_Callback());
    // Create a default BLE Descriptor
    p_ble_console->addDescriptor(new BLE2902());
    
    
    // Start the service
    p_ble_service->start();


    // Start advertising
    BLEAdvertising *p_ble_advertising = BLEDevice::getAdvertising();
    p_ble_advertising->addServiceUUID(SERVICE_UUID);
    p_ble_advertising->setScanResponse(false);
    p_ble_advertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
    BLEDevice::startAdvertising();
  }

  

  int logger_interval_ms = 2000;
  int audio_logger_prev_time_ms = 0;

  void update_audio(void* pvParameters){
    while(audio_update_loop){
      uint8_t mic_value = (uint8_t)analogRead(MIC_PIN);
      analogWrite(SPEAKER_PIN, mic_value);
      if ((mic_value>127) && (millis()-audio_logger_prev_time_ms > logger_interval_ms)){
        ble_logger.log("Loud sound detected");
        vTaskDelay(100/portTICK_PERIOD_MS); // Delay for 100 ms
        audio_logger_prev_time_ms = millis();
      }
      vTaskDelay(1 / portTICK_PERIOD_MS); // Delay for 100 ms
    }
  }


  void main_loop(){
    // Main loop for the logic handler
    if (device_connected) {
      p_ble_char->setValue(std::string("Here"));
      p_ble_char->notify();
      
      ble_logger.log("Another test message");
      value++;
      delay(500);
    }
    
    // While disconnected 
    if (!device_connected && old_device_connected) {
      delay(500); // Give the bluetooth stack the chance to get things ready
      p_bleserver->startAdvertising(); // Restart advertising
      old_device_connected = device_connected;
    }
    // While pairing/connecting to a device
    if (device_connected && !old_device_connected) {
      old_device_connected = device_connected;
      delay(300);
    }
    delay(10);
    loop_count++;
  }



}

// Entry point for the program
void setup() {
  Lamp::set_time_comp_time();
  Lamp::light.flash(127, 127, 127, 3); // Bootup light
  
  Serial.begin(115200);
  while (!Serial) {;}
  
  Serial.println("Starting BLE work!");
  Lamp::setup_BLE();
  Lamp::ble_logger = BLELogger(Lamp::p_ble_console);
  Lamp::ble_logger.log("BLE Console started");

  std::cout<<"This might print to serial.";
  delay(500);
  xTaskCreate(Lamp::update_audio, "Audio", 10000, NULL, 1, NULL); // Create a task for the audio update loop

  Lamp::light.flash(90,64,64,3); // End of setup light  
}

// Primary ongoing loop
void loop() {Lamp::main_loop();}



