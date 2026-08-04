from typing import TypeVar, Protocol

from scarf.drivers.interfaces import Device

T = TypeVar("T")


class Driver[T](Protocol):
    hostname: str
    version: str
    serial_number: str
    model: str
    hwsku: str
    system_mac: str | None

    @classmethod
    async def from_device(cls, device: Device) -> T | None:
        """Return True if this driver can be used for the given device."""
        raise NotImplementedError
