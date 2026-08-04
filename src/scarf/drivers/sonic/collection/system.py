from typing import Iterable
from pydantic import BaseModel
from scarf.drivers.interfaces import Device
from scarf.utils import split_keyval
from scarf.drivers.helpers import _verify_helper
from scarf.drivers.sonic.helpers import _parse_show_keyval


class IsSonic(BaseModel):
    is_sonic: bool = True

    def __bool__(self):
        return self.is_sonic

    @classmethod
    async def collect(cls, device: Device) -> "IsSonic":
        status, _, _ = await device.run("[ -f /etc/sonic/sonic_version.yml ]")
        return cls(is_sonic=status == 0)

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg


class Hostname(BaseModel):
    hostname: str = ""
    fqdn: str | None = None

    def __str__(self):
        return self.hostname

    @classmethod
    async def collect(cls, device: Device) -> "Hostname":
        status, out, err = await device.run("uname -n")

        if status != 0:
            raise ValueError(f"Failed to collect hostname: {err}")

        return cls(hostname=out.strip())

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg


class SySyseeprom(BaseModel):
    sku: str
    serial_number: str
    mac: str
    mfg_time: str
    mfg_time2: str
    sid: str

    @classmethod
    async def collect(cls, device: Device) -> "SySyseeprom":
        status, out, err = await device.run("show platform syseeprom")
        if status != 0:
            raise ValueError(f"Failed to collect sysinfo: {err}")

        syseeprom_data = _parse_show_platform_syseeprom(out)
        if "mfg_time2" not in syseeprom_data:
            syseeprom_data["mfg_time2"] = ""
        
        return cls(
            sku=syseeprom_data["sku"],
            serial_number=syseeprom_data["serial_number"],
            mac=syseeprom_data["mac"],
            mfg_time=syseeprom_data["mfg_time"],
            mfg_time2=syseeprom_data["mfg_time2"],
            sid=syseeprom_data["sid"],
        )

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg


class Version(BaseModel):
    version: str
    platform: str
    hwsku: str
    serial_number: str
    model_number: str
    hardware_revision: str
    uptime: str

    @classmethod
    async def collect(cls, device: Device) -> "Version":
        status, out, err = await device.run("show version")
        if status != 0:
            raise ValueError(f"Failed to collect sysinfo: {err}")
        version_data = _parse_show_version(out)
        return cls(
            version=version_data["version"],
            platform=version_data["platform"],
            hwsku=version_data["hwsku"],
            serial_number=version_data["serial_number"],
            model_number=version_data["model_number"],
            hardware_revision=version_data["hardware_revision"],
            uptime=version_data["uptime"],
        )

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg


class SysInfo(BaseModel):
    hostname: Hostname
    version: Version
    syseeprom: SySyseeprom

    @classmethod
    async def collect(cls, device: Device) -> "SysInfo":
        return cls(
            hostname=await Hostname.collect(device),
            version=await Version.collect(device),
            syseeprom=await SySyseeprom.collect(device),
        )

    def verify(self, wanted: "SysInfo | None") -> Iterable[tuple[bool, str, str]]:
        if wanted is None:
            return

        if self.version.serial_number != self.syseeprom.serial_number:
            yield False, "version.serial_number", "Serial number mismatch"

        for ok, field, msg in self.version.verify(wanted.version):
            yield ok, f"version.{field}", msg

        for ok, field, msg in self.syseeprom.verify(wanted.syseeprom):
            yield ok, f"syseeprom.{field}", msg


def _parse_show_version(output: str):
    """
    Collect data from `show version`

    Example output:
    ```
    SONiC Software Version: SONiC.20241211.21
    SONiC OS Version: 12
    Distribution: Debian 12.9
    Kernel: 6.1.0-29-2-amd64
    Build commit: 587de3740c
    Build date: Fri May 30 06:03:05 UTC 2025
    Built by: azureuser@66a57304c000000

    Platform: x86_64-arista_7060x6_16pe_384c_b
    HwSKU: Arista-7060X6-16PE-384C-O128S2
    ASIC: broadcom
    ASIC Count: 1
    Serial Number: SSN25202353
    Model Number: DCS-7060X6-16PE-384C
    Hardware Revision: 03.00
    Uptime: 18:52:52 up 4 days, 17:36,  1 user,  load average: 1.42, 1.33, 1.13
    Date: Mon 27 Apr 2026 18:52:52```
    """
    data = {}
    for line in output.splitlines():
        if "SONiC Software Version:" in line:
            _, data["version"] = split_keyval(line)
        elif "Platform:" in line:
            data["platform"] = line.split(":")[-1].strip()
        elif "HwSKU:" in line:
            data["hwsku"] = line.split(":")[-1].strip()
        elif "Serial Number:" in line:
            data["serial_number"] = line.split(":")[-1].strip()
        elif "Model Number:" in line:
            data["model_number"] = line.split(":")[-1].strip()
        elif "Hardware Revision:" in line:
            data["hardware_revision"] = line.split(":")[-1].strip()
        elif "Uptime:" in line:
            data["uptime"] = line.split(":")[-1].strip()
    return data


def _parse_show_platform_syseeprom(output: str):
    """
    Collect data from `show platform syseeprom`

    Example output:
    ```
    ASY: ASY088971103
    HwApi: 03.00
    HwRev: 10.11
    MAC: b8:a1:b8:a2:94:67
    MfgTime: 20200101000000
    MfgTime2: 20250728220810
    SID: Moby
    SKU: DCS-7060X6-16PE-384C
    SerialNumber: SSN25202353
    ```
    """
    data = _parse_show_keyval(output)
    
    return {
        "sku": "(unknown)",
        "serial_number": "(unknown)",
        "mac": "(unknown)",
        "mfg_time": "(unknown)",
        "mfg_time2": "(unknown)",
        "sid": "(unknown)",
    } | data


__all__ = ["SysInfo", "SySyseeprom", "Version"]


async def main():
    device = Device_("moby253")
    await device.connect()
    sysinfo = await SysInfo.collect(device)
    print(sysinfo)
    await device.close()


if __name__ == "__main__":
    import asyncio
    from ahab.device import Device as Device_

    asyncio.run(main())
