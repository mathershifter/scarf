from collections.abc import Iterable

from pydantic import BaseModel, RootModel

from scarf.drivers.helpers import _verify_helper
from scarf.drivers.interfaces import Device
from scarf.drivers.sonic.helpers import _parse_show_table


class Psu(BaseModel):
    psu: str
    model: str | None
    serial: str | None
    hw_rev: str | None
    voltage: str | None
    current: str | None
    power: str | None
    status: str | None
    led: str | None

    @property
    def slug(self) -> str:
        return self.psu.lower().replace(" ", "-")

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)


class Psus(RootModel):
    root: list[Psu]

    @classmethod
    async def collect(cls, device: Device) -> "Psus":
        status, out, err = await device.run("show platform psustatus")
        if status != 0:
            raise ValueError(f"Failed to collect psus: {err}")

        return cls(
            [
                Psu(
                    psu=p["psu"],
                    model=p["model"],
                    serial=p["serial"],
                    hw_rev=p["hw_rev"],
                    voltage=p["voltage"],
                    current=p["current"],
                    power=p["power"],
                    status=p["status"],
                    led=p["led"],
                )
                for p in _parse_show_table(str(out))
            ]
        )

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        yield from _verify_helper(self, wanted)


# def _parse_show_platform_psustatus(output: str):
#     """
#     PSU    Model    Serial    HW Rev    Voltage (V)    Current (A)    Power (W)    Status    LED
#     -----  -------  --------  --------  -------------  -------------  -----------  --------  -----
#     PSU 1  N/A      N/A       N/A       N/A            N/A            N/A          OK        off
#     PSU 2  N/A      N/A       N/A       N/A            N/A            N/A          OK        off
#     """

#     data = []

#     for line in output.splitlines()[2:]:
#         fields = ["psu", "model", "serial", "hw_rev", "voltage", "current",
#                   "power", "status", "led"]

#         parts = re.split(r"\s{2,}", line.strip())
#         parts = parts + [None] * (len(fields) - len(parts))

#         d = dict(zip(fields, parts))
#         data.append(d)
#     return data


async def main():
    device = Device_("moby253")
    await device.connect()
    psus = await Psus.collect(device)
    for p in psus.root:
        print(p.psu, p.status)
    await device.close()


if __name__ == "__main__":
    import asyncio

    from scarf.device import Device as Device_

    asyncio.run(main())
