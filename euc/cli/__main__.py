import logging
import ravel
import asyncio
import euc.device


async def run_cli(system_bus):
    devices = await euc.device.list(system_bus)
    print("detected devices:", devices)
    loop = asyncio.get_event_loop()
    for device in devices:
        device.add_properties_changed_callback(
            lambda self, props: print(f"{self.properties!r}")
        )
        loop.create_task(device.run())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    system_bus = ravel.system_bus()
    loop = asyncio.get_event_loop()
    system_bus.attach_asyncio(loop)
    loop.create_task(run_cli(system_bus))
    loop.run_forever()
