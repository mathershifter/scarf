from collections.abc import Iterable

from scarf.drivers.driver import Driver
from scarf.drivers.eos import EOSDriver
from scarf.drivers.interfaces import Collector, Device, Verifier
from scarf.drivers.sonic import SONiCDriver

DRIVERS = [SONiCDriver, EOSDriver]


async def from_device(device: Device) -> Driver | None:
    """Return a driver for the given device."""
    for d in DRIVERS:
        driver = await d.from_device(device)  # type: ignore[attr-defined]
        if driver is not None:
            return driver
    return None


async def collect[T](device: Device, collector: Collector[T]) -> T:
    """Collect data from the device."""
    c = await collector.collect(device)
    return c


async def verify(
    device: Device, verifier: Verifier, wanted: Iterable[tuple[str, str]] | None
) -> Iterable[tuple[bool, str, str]]:
    """Verify data from the device."""

    return verifier.verify(wanted)


__all__ = [
    "DRIVERS",
    "Driver",
    "EOSDriver",
    "SONiCDriver",
    "collect",
    "from_device",
    "verify",
]
