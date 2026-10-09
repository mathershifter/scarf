from pydantic import BaseModel

from scarf.drivers.eos.collection.system import IsEOS, SysInfo
from scarf.drivers.interfaces import Device


class EOSDriver(BaseModel):
    hostname: str
    version: str
    serial_number: str
    model: str
    hwsku: str | None
    system_mac: str | None

    @classmethod
    async def from_device(cls, device: Device) -> "EOSDriver | None":
        """Return True if this driver can be used for the given device."""

        if not await IsEOS.collect(device):
            return None

        sys_info = await SysInfo.collect(device)
        
        return cls(
            hostname=sys_info.hostname,
            version=sys_info.version.version,
            serial_number=sys_info.version.serial_number,
            model=sys_info.version.model,
            hwsku=sys_info.version.hwsku,
            system_mac=sys_info.version.sys_mac_address,
        )