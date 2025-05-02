from bleak import BleakClient
import time

DEVICE_ADDRESS = "F4:12:FA:FA:0E:A9"
CONSOLE_UUID = "311b1fd7-7411-4d89-afcc-0fb165f4aac8"
CHARACTERISTIC_UUID = "005e1887-1150-43e5-a985-b1b741437ea6"


async def write_ble():
    async with BleakClient(DEVICE_ADDRESS) as client:
        prev_data_str = "a"

        print(f"Connected to {DEVICE_ADDRESS}")
        await client.write_gatt_char(CHARACTERISTIC_UUID, "writing".encode("utf-8"), response=True)
        print("Data written successfully!")


import asyncio
asyncio.run(write_ble())