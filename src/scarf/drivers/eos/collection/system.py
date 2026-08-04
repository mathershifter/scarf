from typing import Iterable
from pydantic import BaseModel
from ahab.drivers.interfaces import Device
from ahab.drivers.helpers import _verify_helper


class IsEOS(BaseModel):
    is_eos: bool = True

    def __bool__(self):
        return self.is_eos

    @classmethod
    async def collect(cls, device: Device) -> "IsEOS":
        status, _, _ = await device.run("[ -f /etc/Eos-release ]")
        return cls(is_eos=status == 0)

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg
