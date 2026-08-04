import json
from pydantic import BaseModel, RootModel

from scarf.drivers.interfaces import Device
from scarf.conv import iorn, forn


class InterfaceCounters(BaseModel):
    interface_name: str
    rx_bps: float | None
    rx_drp: int | None
    rx_err: int | None
    rx_ok: int | None
    rx_ovr: int | None
    rx_util: float | None
    tx_bps: float | None
    tx_drp: int | None
    tx_err: int | None
    tx_ok: int | None
    tx_ovr: int | None
    tx_util: float | None
    state: str | None


class InterfacesCounters(RootModel):
    root: list[InterfaceCounters]

    @classmethod
    async def collect(cls, device: Device) -> "InterfacesCounters":
        status, counters_output, err = await device.run("show interfaces counters -j")
        if status != 0:
            raise ValueError(f"Failed to collect interface counters: {err}")

        data = json.loads(counters_output)
        root = []
        for name, counters in data.items():
            counters = {
                k.lower(): v for k, v in counters.items() if k != "interface_name"
            }
            root.append(
                InterfaceCounters(
                    interface_name=name,
                    rx_bps=forn(counters.get("rx_bps")),
                    rx_drp=iorn(counters.get("rx_drp")),
                    rx_err=iorn(counters.get("rx_err")),
                    rx_ok=iorn(counters.get("rx_ok")),
                    rx_ovr=iorn(counters.get("rx_ovr")),
                    rx_util=forn(counters.get("rx_util")),
                    tx_bps=forn(counters.get("tx_bps")),
                    tx_drp=iorn(counters.get("tx_drp")),
                    tx_err=iorn(counters.get("tx_err")),
                    tx_ok=iorn(counters.get("tx_ok")),
                    tx_ovr=iorn(counters.get("tx_ovr")),
                    tx_util=forn(counters.get("tx_util")),
                    state=counters.get("state"),
                )
            )

        return cls(root)


class InterfaceCountersFec(BaseModel):
    interface_name: str
    fec_corr: int | None
    fec_post_ber: float | None
    fec_pre_ber: float | None
    fec_symbol_err: int | None
    fec_uncorr: int | None
    state: str | None


class InterfacesCountersFec(RootModel):
    root: list[InterfaceCountersFec]

    def get_interface(self, name: str) -> InterfaceCountersFec | None:
        for c in self.root:
            if c.interface_name == name:
                return c
        return None

    @classmethod
    async def collect(cls, device: Device) -> "InterfacesCountersFec":
        status, counters_output, err = await device.run(
            "show interfaces counters fec-stats -j"
        )
        if status != 0:
            raise ValueError(f"Failed to collect interface counters: {err}")

        data = json.loads(counters_output)
        root = []
        for name, counters in data.items():
            counters = {
                k.lower(): v for k, v in counters.items() if k != "interface_name"
            }
            # sanitized = {k: numerize(v) for k, v in counters.items()}
            root.append(
                InterfaceCountersFec(
                    interface_name=name,
                    fec_corr=iorn(counters.get("fec_corr")),
                    fec_post_ber=forn(counters.get("fec_post_ber")),
                    fec_pre_ber=forn(counters.get("fec_pre_ber")),
                    fec_symbol_err=iorn(counters.get("fec_symbol_err")),
                    fec_uncorr=iorn(counters.get("fec_uncorr")),
                    state=counters.get("state"),
                )
            )

        return cls(root)


async def main():
    device = Device_("moby253")
    await device.connect()
    counters = await InterfacesCounters.collect(device)
    for c in counters.root:
        print(c.interface_name, c.rx_bps, c.tx_bps)

    counters = await InterfacesCountersFec.collect(device)
    for c in counters.root:
        print(c.interface_name, c.fec_corr, c.fec_uncorr)

    await device.close()


if __name__ == "__main__":
    import asyncio
    from scarf.device import Device as Device_

    asyncio.run(main())
