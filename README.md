# Bluetooth Lamp

A BLE-controlled RGB lamp running on an ESP32-S3, with a Python desktop GUI for wireless configuration.

## Overview

The lamp supports four modes, all configurable from the GUI over Bluetooth Low Energy:

- **Normal** — static colour set from the GUI
- **Metronome** — flashes at a user-set BPM
- **Fade** — smoothly cycles through three user-selected colours
- **Note Match** — flashes the colour mapped to the detected musical pitch (FFT-based audio analysis)

Each of the 48 notes across 4 octaves (A1–Ab4) has an individually configurable colour, stored per user in a local SQLite database.

## Structure

```
firmware/   ESP32-S3 firmware (C++, PlatformIO + Arduino framework)
gui/        Desktop control app (Python, CustomTkinter + SQLite + Bleak)
```

## Hardware

- **Board:** ESP32-S3 DevKitC-1
- **LEDs:** External RGB (GPIO 4/5/6) + built-in neopixel
- **Microphone:** GPIO 16 (ADC input)
- **Speaker:** GPIO 18 (DAC output, passthrough)

## Getting Started

### Firmware

```sh
cd firmware
pio run -t upload   # build and flash
pio run -t monitor  # serial output at 115200 baud
```

### GUI

```sh
cd gui
python setup.py     # install dependencies
python samples.py   # create userdata.db with a default user
python main_GUI.py  # launch the app
```

Default login: username `Mike`, password `12345678`.

## BLE Details

- Device name: `ESP32`
- Service UUID: `4c3c2810-045d-4880-a1b2-e9143e397613`
- Control characteristic: `005e1887-1150-43e5-a985-b1b741437ea6`
- Console characteristic: `311b1fd7-7411-4d89-afcc-0fb165f4aac8`

The device MAC address is hardcoded in the GUI and test scripts as `F4:12:FA:FA:0E:A9` — update this to match your hardware.
