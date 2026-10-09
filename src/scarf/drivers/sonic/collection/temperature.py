from collections.abc import Iterable
from functools import cached_property

from pydantic import BaseModel, RootModel

from scarf.drivers.helpers import _verify_helper
from scarf.drivers.interfaces import Device
from scarf.drivers.sonic.helpers import _parse_show_table


class Sensor(BaseModel):
    sensor: str
    temperature: float
    high_th: int
    low_th: int
    crit_high_th: int
    crit_low_th: int
    warning: str

    _name: str | None = None

    def __bool__(self):
        return not self.warning

    def __str__(self):
        return f"{self.slug}={self.temperature}"

    @cached_property
    def slug(self) -> str:
        return self.sensor.lower().replace(" ", "-")

    @cached_property
    def short_slug(self) -> str:
        return self.name.lower().replace(" ", "-")

    @cached_property
    def name(self) -> str:
        name = self.sensor
        # remove redundant words
        name = name.replace("temp sensor", "").strip()
        name = name.replace("internal sensor", "Internal").strip()
        name = name.title()
        return name


class Temperatures(RootModel):
    root: list[Sensor]

    @classmethod
    async def collect(cls, device: Device) -> "Temperatures":
        status, out, err = await device.run("show platform temperature")
        if status != 0:
            raise ValueError(f"Failed to collect temperature: {err}")
        data = _parse_show_table(str(out))
        return cls([Sensor(**item) for item in data])

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)

    def get_sensor(self, name: str) -> Sensor | None:
        for s in self.root:
            if s.slug == name or s.short_slug or s.sensor == name:
                return s
        return None


async def main():
    device = Device_("moby253")
    await device.connect()
    temps = await Temperatures.collect(device)
    for t in temps.root:
        print(t.short_slug, t.temperature)
    await device.close()


if __name__ == "__main__":
    import asyncio

    from scarf.device import Device as Device_

    asyncio.run(main())
