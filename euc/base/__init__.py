import asyncio

# from abc import abstractmethod, ABC
from collections import defaultdict

import ravel
import logging

logger = logging.getLogger(__name__)


class BLEDevice:
    def __init__(self, system_bus, device_path, device_info):
        self.system_bus = system_bus
        self.bluez = system_bus["org.bluez"]
        self.device_path = device_path
        self.device_info = device_info
        self.is_connected = False

        self.system_bus.listen_propchanged(
            path="/", fallback=True, interface=None, func=self.obj_prop_changed
        )

    @classmethod
    def from_device(cls, system_bus, device_path, device_info, **kwargs):
        return cls(system_bus, device_path, device_info, **kwargs)

    async def connect(self):
        device_itf = await self.bluez[self.device_path].get_async_interface(
            "org.bluez.Device1"
        )
        await device_itf.Connect()
        self.is_connected = await device_itf.Connected
        return device_itf

    async def get_managed_objects(self):
        itf = await self.bluez["/"].get_async_interface(
            "org.freedesktop.DBus.ObjectManager"
        )
        return (await itf.GetManagedObjects())[0]

    async def get_characteristic_path_by_uuid(self, uuid):
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def is_char_ok(gatt_char_dict):
            gatt_char_props = gatt_char_dict.get("org.bluez.GattCharacteristic1")
            return gatt_char_props and gatt_char_props["UUID"][1] == uuid

        @ravel.signal(
            name="object_added",
            in_signature="oa{sa{sv}}",
            path_keyword="object_path",
            args_keyword="args",
        )
        def objects_added(object_path, args):
            path = args[0]
            if not path.startswith(self.device_path):
                return
            if is_char_ok(args[1]):
                self.system_bus.unlisten_objects_added(objects_added)
                future.set_result((path, args[1]))

        async def get_path():
            managed_objects = await self.get_managed_objects()
            return next(
                (
                    (path, obj)
                    for path, obj in managed_objects.items()
                    if is_char_ok(obj)
                ),
                None,
            )

        self.system_bus.listen_objects_added(objects_added)
        try:
            for f in asyncio.as_completed([get_path(), future], timeout=10):
                path = await f
                if path:
                    return path
        finally:
            self.system_bus.unlisten_objects_added(objects_added)

    async def get_characteristic_itf_by_uuid(self, uuid):
        path, obj = await self.get_characteristic_path_by_uuid(uuid)
        characteristic_itf = await self.bluez[path].get_async_interface(
            "org.bluez.GattCharacteristic1"
        )
        return characteristic_itf, obj

    @ravel.signal(
        name="prop_changed",
        path_keyword="object_path",
        in_signature="sa{sv}as",
        arg_keys=("interface_name", "changed_properties", "invalidated_properties"),
    )
    def obj_prop_changed(
        self, object_path, interface_name, changed_properties, invalidated_properties
    ):
        if object_path.startswith(self.device_path):
            if object_path == self.device_path and "Connected" in changed_properties:
                self.is_connected = changed_properties["Connected"][1]
            self.on_properties_changed(
                object_path, interface_name, changed_properties, invalidated_properties
            )

    def on_properties_changed(
        self, object_path, interface_name, changed_properties, invalidated_properties
    ):
        pass


class EUCBase(BLEDevice):
    def __init__(self, system_bus, device_path, device_info):
        super().__init__(system_bus, device_path, device_info)

        self._prop_callbacks = defaultdict(list)
        self._props_callbacks = []
        self._properties = {}

    @property
    def unique_id(self):
        return self.device_path.rsplit("/", 1)[1]

    @property
    def name(self):
        return self.device_info["Name"][1]

    def add_property_changed_callback(self, cb, prop_name="ANY"):
        self._prop_callbacks[prop_name].append(cb)

    def add_properties_changed_callback(self, cb):
        self._props_callbacks.append(cb)

    def update_properties(self, props):
        for prop_name, value in props.items():
            self.update_property(prop_name, value)
        for cb in self._props_callbacks:
            cb(self, props)

    def update_property(self, prop_name, value):
        if self._properties.get(prop_name) != value:
            self._properties[prop_name] = value
            for cb in self._prop_callbacks[prop_name]:
                cb(self, prop_name, value)
            for cb in self._prop_callbacks["ANY"]:
                cb(self, prop_name, value)

    @property
    def properties(self):
        return self._properties
