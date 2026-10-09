import enum
from collections.abc import Iterable

from pydantic import BaseModel, RootModel, field_validator

from scarf.drivers.helpers import _verify_helper
from scarf.drivers.interfaces import Device
from scarf.drivers.sonic.helpers import _parse_show_table


class MonitorType(enum.StrEnum):
    PROGRAM = "program"
    PROCESS = "process"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    FAN = "fan"
    PSU = "psu"


class MonitoredItem(BaseModel):
    name: str
    status: str
    type: MonitorType

    def __bool__(self):
        return self.status == "ok"

    @field_validator("type", mode="before")
    def _normalize_type(cls, v: str) -> MonitorType:
        return MonitorType(v.lower())

    @field_validator("status")
    def _normalize_status(cls, v: str) -> str:
        lower = v.lower()
        if lower == "not ok":
            return "failed"
        return lower

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)


class SystemHealth(RootModel):
    root: list[MonitoredItem]

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)

    @classmethod
    async def collect(cls, device: Device) -> "SystemHealth":
        status, out, err = await device.run("sudo show system-health monitor-list")
        if status != 0:
            raise ValueError(f"Failed to collect system health: {err}")

        return cls([MonitoredItem(**item) for item in _parse_show_table(str(out))])


async def main():
    device = Device_("moby253")
    await device.connect()
    health = await SystemHealth.collect(device)
    for h in health.root:
        print(h.name, h.type, h.status)
    await device.close()


if __name__ == "__main__":
    import asyncio

    from scarf.device import Device as Device_

    asyncio.run(main())
