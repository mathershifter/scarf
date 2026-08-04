from pydantic import BaseModel
from scarf.drivers.interfaces import Device


class EOSDriver(BaseModel):
    hostname: str
    version: str
    serial_number: str
    model: str
    hwsku: str
    system_mac: str | None

    @classmethod
    async def from_device(cls, device: Device) -> "EOSDriver | None":
        """Return True if this driver can be used for the given device."""
        return None
