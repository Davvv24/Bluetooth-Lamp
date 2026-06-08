from bleak import BleakClient
import time
import keyboard as kb

DEVICE_ADDRESS = "F4:12:FA:FA:0E:A9"
CONSOLE_UUID = "311b1fd7-7411-4d89-afcc-0fb165f4aac8"
CHARACTERISTIC_UUID = "005e1887-1150-43e5-a985-b1b741437ea6"


async def read_ble(client):
    prev_data_str = "a"        
    while True:
        if kb.read_key() == "q":
            print("You pressed q")
            break
        try:
            data = await client.read_gatt_char(CONSOLE_UUID)
            try:
                data_str = data.decode(encoding="latin-1")
            except Exception as e:
                print(f"Unicode error:{e}")

            # if data_str!=prev_data_str:
            #     print(f"Received Data: {prev_data_str}")
            #     prev_data_str = data_str
            print(f"Received Data: {data.decode(encoding="latin-1")}")
            # await asyncio.sleep(1)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break  # Stop if there's a failure


async def write_ble(client):
    await asyncio.sleep(3)
    await client.write_gatt_char(CHARACTERISTIC_UUID, "writing".encode("utf-8"), response=True)
    print("Data written successfully!")
    await asyncio.sleep(3)
    await client.write_gatt_char(CHARACTERISTIC_UUID, "writing".encode("utf-8"), response=True)
    print("Data written successfully again!")


async def main():
    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"Connected to {DEVICE_ADDRESS}")

        # Run write and read tasks asynchronously
        await asyncio.gather(write_ble(client), read_ble(client))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())