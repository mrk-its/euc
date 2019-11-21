import asyncio
from abc import abstractmethod, ABC
from collections import defaultdict
import pkg_resources


class EUCBase(ABC):
    def __init__(self, system_bus, device_path, device_info):
        self.system_bus = system_bus
        self.device_path = device_path
        self.device_info = device_info

        self._prop_callbacks = defaultdict(list)
        self._props_callbacks = []

        self._properties = {}

        self.bluez = system_bus["org.bluez"]

    @classmethod
    def from_device(cls, system_bus, device_path, device_info):
        return cls(system_bus, device_path, device_info)

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
