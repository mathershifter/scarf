from collections.abc import Iterable

from pydantic import BaseModel, RootModel

from scarf.drivers.helpers import _verify_helper
from scarf.drivers.interfaces import Device
from scarf.drivers.sonic.helpers import _parse_show_table


class Fan(BaseModel):
    drawer: str
    led: str
    fan: str
    speed: str
    direction: str
    presence: str
    status: str

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)


class Fans(RootModel):
    root: list[Fan]

    @classmethod
    async def collect(cls, device: Device) -> "Fans":
        status, out, err = await device.run("show platform fan")
        if status != 0:
            raise ValueError(f"Failed to collect fans: {err}")

        return cls(
            [
                Fan(
                    drawer=f["drawer"],
                    led=f["led"],
                    fan=f["fan"],
                    speed=f["speed"],
                    direction=f["direction"],
                    presence=f["presence"],
                    status=f["status"],
                )
                for f in _parse_show_table(str(out))
            ]
        )

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)


async def main():
    device = Device_("moby253")
    await device.connect()
    fans = await Fans.collect(device)
    for f in fans.root:
        print(f.fan, f.speed)
    await device.close()


if __name__ == "__main__":
    import asyncio

    from scarf.device import Device as Device_

    asyncio.run(main())
