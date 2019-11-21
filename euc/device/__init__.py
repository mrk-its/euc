import pkg_resources
import euc.base


BLUEZ_DEVICE_INTF = "org.bluez.Device1"
UUIDS = "UUIDs"


def ble_service_handlers():
    return (
        (entry_point.name, entry_point.load())
        for entry_point in pkg_resources.iter_entry_points("ble.service.handler")
    )


def euc_service_handlers():
    return (
        (name, driver_class)
        for name, driver_class in ble_service_handlers()
        if issubclass(driver_class, euc.base.EUCBase)
    )


async def list(system_bus, device_path=None):
    known_services = dict(euc_service_handlers())
    bluez = system_bus["org.bluez"]
    itf = await bluez["/"].get_async_interface("org.freedesktop.DBus.ObjectManager")
    managed_objects = (await itf.GetManagedObjects())[0]
    handlers = []
    for path, obj in managed_objects.items():
        device_itf = obj.get(BLUEZ_DEVICE_INTF)
        if not device_itf or UUIDS not in device_itf:
            continue
        if device_path and path != device_path:
            continue
        uuids = device_itf[UUIDS][1]
        for uuid in uuids:
            handler_class = known_services.get(uuid)
            if handler_class:
                handlers.append(handler_class.from_device(system_bus, path, device_itf))
    return handlers
