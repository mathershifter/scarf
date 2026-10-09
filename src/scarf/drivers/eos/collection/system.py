import json
from collections.abc import Iterable

from pydantic import BaseModel

from scarf.drivers.helpers import _verify_helper
from scarf.drivers.interfaces import Device


class IsEOS(BaseModel):
    is_eos: bool = True

    def __bool__(self):
        return self.is_eos

    @classmethod
    async def collect(cls, device: Device) -> "IsEOS":
        status, _, _ = await device.run("bash [ -f /etc/Eos-release ]")
        return cls(is_eos=status == 0)

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)

class Version(BaseModel):
    """
    {
        "mfgName": "Arista",
        "modelName": "DCS-7060X6-32PE-F",
        "hardwareRevision": "11.02",
        "serialNumber": "HBG253303CB",
        "systemMacAddress": "a8:8f:99:03:b4:26",
        "hwMacAddress": "a8:8f:99:03:b4:26",
        "configMacAddress": "00:00:00:00:00:00",
        "version": "4.34.2F",
        "architecture": "x86_64",
        "internalVersion": "4.34.2F-43232954.4342F",
        "internalBuildId": "fa4f3f20-cd56-4a28-a392-ebc438812800",
        "imageFormatVersion": "3.0",
        "imageOptimization": "Default",
        "bootupTimestamp": 1781648318.1724234,
        "uptime": 4328554.1,
        "memTotal": 32629688,
        "memFree": 28852376,
        "isIntlVersion": false
    }
    """
    version: str
    platform: str | None = None
    hwsku: str | None = None
    hardware_revision: str | None = None
    model: str
    serial_number: str
    uptime: float | None = None
    

    @classmethod
    async def collect(cls, device: Device) -> "Version":
        status, out, err = await device.run("show version | json")

        if status != 0:
            raise ValueError(f"Failed to collect version info: {err}")

        data = json.loads(out)

        return cls(
            version=data["version"],
            platform=data.get("architecture"),
            hwsku=data["modelName"],
            serial_number=data["serialNumber"],
            model=data["modelName"],
            hardware_revision=data["hardwareRevision"],
            uptime=data.get("uptime")
        )

class Hostname(BaseModel):
    hostname: str
    fqdn: str | None = None

    @classmethod
    async def collect(cls, device: Device) -> "Hostname":
        status, out, err = await device.run("show hostname | json")

        if status != 0:
            raise ValueError(f"Failed to collect hostname info: {err}")

        data = json.loads(out)

        return cls(
            hostname=data["hostname"],
            fqdn=data.get("fqdn")
        )

class SysInfo(BaseModel):
    hostname: str
    version: Version

    @classmethod
    async def collect(cls, device: Device) -> "SysInfo":
        version = await Version.collect(device)
        hostname = await Hostname.collect(device)
        return cls(
            hostname=hostname.hostname,
            version=version
        )

__all__ = ["Hostname", "IsEOS", "SysInfo", "Version"]