#include "main.hpp"

namespace Lamp {

ESPLight light(RED_PIN, GREEN_PIN, BLUE_PIN, true);

// ── BLE Callbacks ─────────────────────────────────────────────────────────────
// These run inside the BLE stack task.  NEVER call blocking functions (delay,
// light.flash) here — the BLE task has a small stack and tight timing, which is
// the root cause of the 10-second crash seen in earlier versions.
// Only touch shared state variables; all hardware interaction stays in main_loop.

class BLE_Server_Callback : public BLEServerCallbacks {
    void onConnect(BLEServer*) {
        device_connected = true;
        light.set(0, 100, 0);   // instant green — no blocking delay
    }
    void onDisconnect(BLEServer*) {
        device_connected = false;
        light.set(100, 0, 0);   // instant red
    }
};

class BLE_Char_Callback : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* p_char) {
        std::string value = p_char->getValue();
        if (value.length() < 2) return;

        uint8_t cmd = (uint8_t)value[0];
        uint8_t val = (uint8_t)value[1];

        if (cmd >= 200 && cmd < 204) {
            // Mode switch: 200=Metronome, 201=Note Match, 202=Normal, 203=Fade
            current_mode = cmd - 200;
            EEPROM.write(200, current_mode);
            eeprom_dirty = true;

        } else if (cmd == 205) {
            // BPM — clamp so flash duration stays within watchdog budget
            bpm = max(30.0f, min(220.0f, float(val)));
            EEPROM.write(201, val);
            eeprom_dirty = true;

        } else if (cmd > 0 && cmd <= BUTTONS * 3) {
            // Colour mapping: 3 commands per button (R then G then B)
            int index   = (cmd - 1) / 3;
            int channel = (cmd - 1) % 3;
            float fval  = val / 255.0f;
            switch (channel) {
                case 0: rgb_mapping[index].r = fval; EEPROM.write(index * 3,     val); break;
                case 1: rgb_mapping[index].g = fval; EEPROM.write(index * 3 + 1, val); break;
                case 2: rgb_mapping[index].b = fval; EEPROM.write(index * 3 + 2, val); break;
            }
            eeprom_dirty = true;
        }
    }
};

// ── EEPROM ────────────────────────────────────────────────────────────────────

void load_from_eeprom() {
    EEPROM.begin(EEPROM_SIZE);

    uint8_t stored_mode = EEPROM.read(200);
    current_mode = (stored_mode <= 3) ? stored_mode : 2;  // default: Normal

    uint8_t stored_bpm = EEPROM.read(201);
    bpm = (stored_bpm >= 30 && stored_bpm <= 220) ? float(stored_bpm) : 90.0f;

    rgb_mapping.clear();
    for (int i = 0; i < BUTTONS; i++) {
        uint8_t r = EEPROM.read(i * 3);
        uint8_t g = EEPROM.read(i * 3 + 1);
        uint8_t b = EEPROM.read(i * 3 + 2);
        rgb_mapping.push_back({r / 255.0f, g / 255.0f, b / 255.0f});
    }

    // First-run defaults: if the 5 special colour slots are all black,
    // set something visible so the lamp works immediately after flashing.
    auto is_black = [](const RGB& c) { return c.r == 0.0f && c.g == 0.0f && c.b == 0.0f; };
    if (is_black(rgb_mapping[BUTTONS - 5])) rgb_mapping[BUTTONS - 5] = {0.5f, 0.5f, 0.5f}; // metronome
    if (is_black(rgb_mapping[BUTTONS - 4])) rgb_mapping[BUTTONS - 4] = {0.5f, 0.5f, 0.5f}; // normal
    if (is_black(rgb_mapping[BUTTONS - 3])) rgb_mapping[BUTTONS - 3] = {1.0f, 0.0f, 0.0f}; // fade 1
    if (is_black(rgb_mapping[BUTTONS - 2])) rgb_mapping[BUTTONS - 2] = {0.0f, 1.0f, 0.0f}; // fade 2
    if (is_black(rgb_mapping[BUTTONS - 1])) rgb_mapping[BUTTONS - 1] = {0.0f, 0.0f, 1.0f}; // fade 3
}

// ── BLE setup ─────────────────────────────────────────────────────────────────

void setup_BLE() {
    BLEDevice::init("ESP32");
    p_bleserver = BLEDevice::createServer();
    p_bleserver->setCallbacks(new BLE_Server_Callback());

    BLEService* p_ble_service = p_bleserver->createService(SERVICE_UUID);

    // Control characteristic: GUI writes commands here
    p_ble_char = p_ble_service->createCharacteristic(
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ   |
        BLECharacteristic::PROPERTY_WRITE  |
        BLECharacteristic::PROPERTY_NOTIFY |
        BLECharacteristic::PROPERTY_INDICATE
    );
    p_ble_char->setCallbacks(new BLE_Char_Callback());
    p_ble_char->addDescriptor(new BLE2902());

    // Console characteristic: ESP notifies GUI with log messages (GUI does not write here)
    p_ble_console = p_ble_service->createCharacteristic(
        CONSOLE_UUID,
        BLECharacteristic::PROPERTY_READ   |
        BLECharacteristic::PROPERTY_NOTIFY |
        BLECharacteristic::PROPERTY_INDICATE
    );
    p_ble_console->addDescriptor(new BLE2902());

    p_ble_service->start();

    BLEAdvertising* p_adv = BLEDevice::getAdvertising();
    p_adv->addServiceUUID(SERVICE_UUID);
    p_adv->setScanResponse(false);
    p_adv->setMinPreferred(0x0);
    BLEDevice::startAdvertising();
}

// ── Audio task (FreeRTOS, core 1) ─────────────────────────────────────────────

int audio_logger_prev_time_ms = 0;

void update_audio(void* pvParameters) {
    while (audio_update_loop) {
        uint8_t mic_value = (uint8_t)analogRead(MIC_PIN);
        analogWrite(SPEAKER_PIN, mic_value);
        if (mic_value > 127 && device_connected &&
            (millis() - audio_logger_prev_time_ms > 2000)) {
            ble_logger.log("Loud sound detected");
            audio_logger_prev_time_ms = millis();
        }
        vTaskDelay(1 / portTICK_PERIOD_MS);
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

void set_time_comp_time() {
    struct tm compile_time = {0};
    strptime(__DATE__, "%b %d %Y", &compile_time);
    strptime(__TIME__, "%H:%M:%S", &compile_time);
    time_t t = mktime(&compile_time);
    struct timeval now = {.tv_sec = t};
    settimeofday(&now, NULL);
    printf("Time set to compile date: %s\n", asctime(&compile_time));
}

// ── Main loop ─────────────────────────────────────────────────────────────────

void main_loop() {
    if (rgb_mapping.empty()) { delay(10); return; }

    // BLE connection state — checked at the top of every iteration so reconnect
    // advertising is not blocked by long-running mode animations.
    if (!device_connected && old_device_connected) {
        delay(500);
        p_bleserver->startAdvertising();
        old_device_connected = device_connected;
    }
    if (device_connected && !old_device_connected) {
        old_device_connected = device_connected;
        delay(300);
    }

    // Commit EEPROM writes buffered by the BLE callback.
    // commit() can take 30+ ms (flash write), so we do it here in the main task
    // rather than inside the BLE callback to avoid stalling the BLE stack.
    if (eeprom_dirty) {
        EEPROM.commit();
        eeprom_dirty = false;
    }

    const RGB& metronome_colour = rgb_mapping[BUTTONS - 5];
    const RGB& normal_colour    = rgb_mapping[BUTTONS - 4];
    const RGB& fade1_colour     = rgb_mapping[BUTTONS - 3];
    const RGB& fade2_colour     = rgb_mapping[BUTTONS - 2];
    const RGB& fade3_colour     = rgb_mapping[BUTTONS - 1];

    switch (current_mode) {
        case 0: {
            // Metronome: flash at BPM rate.
            // step_delay controls both fade speed and beat duration —
            // the full flash takes ~128 × step_delay × 3 ms ≈ 75% of one beat.
            int step_delay = max(1, (int)(60000.0f / (bpm * 512)));
            light.flash(metronome_colour, step_delay);
            break;
        }
        case 1: {
            // Note Match — stub; full FFT implementation is Phase 4.
            if (device_connected) ble_logger.log("Note Match not yet implemented");
            delay(2000);
            break;
        }
        case 2: {
            // Normal: hold a constant colour.
            light.set(normal_colour);
            delay(100);
            break;
        }
        case 3: {
            // Fade: smooth 1-second cycle through three user-selected colours.
            // Regenerated each pass so GUI colour changes take effect next cycle.
            std::vector<RGB> fade = generate_fade(fade1_colour, fade2_colour, fade3_colour, 100);
            for (const RGB& step : fade) {
                light.set(step);
                delay(FADE_STEP_MS);
                if (current_mode != 3) break; // mode changed mid-cycle — exit immediately
            }
            break;
        }
        default:
            current_mode = 2;
            break;
    }

    loop_count++;
}

} // namespace Lamp

// ── Arduino entry points ──────────────────────────────────────────────────────

void setup() {
    Lamp::set_time_comp_time();
    Lamp::light.flash(127, 127, 127, 3); // bootup flash

    Serial.begin(115200);
    while (!Serial) {;}

    Serial.println("Loading EEPROM...");
    Lamp::load_from_eeprom();

    Serial.println("Starting BLE...");
    Lamp::setup_BLE();
    Lamp::ble_logger = BLELogger(Lamp::p_ble_console);
    Lamp::ble_logger.log("BLE Console started");

    xTaskCreate(Lamp::update_audio, "Audio", 10000, NULL, 1, NULL);

    Lamp::light.flash(90, 64, 64, 3); // setup complete
}

void loop() { Lamp::main_loop(); }
