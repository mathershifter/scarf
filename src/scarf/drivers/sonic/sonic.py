from pydantic import BaseModel

from scarf.drivers.sonic.collection import SysInfo, IsSonic
from scarf.drivers.interfaces import Device


class SONiCDriver(BaseModel):
    hostname: str
    version: str
    serial_number: str
    model: str
    hwsku: str
    system_mac: str | None

    @classmethod
    async def from_device(cls, device: Device) -> "SONiCDriver | None":
        """Return True if this driver can be used for the given device."""

        is_sonic = await IsSonic.collect(device)
        if not is_sonic:
            return None

        sys_info = await SysInfo.collect(device)

        return cls(
            hostname=sys_info.hostname.hostname,
            version=sys_info.version.version,
            serial_number=sys_info.version.serial_number,
            model=sys_info.version.model_number,
            hwsku=sys_info.version.hwsku,
            system_mac=sys_info.syseeprom.mac,
        )
