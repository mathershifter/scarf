import io
from pydantic import BaseModel
from scarf.drivers.interfaces import Device


class TechSupport(BaseModel):
    path: str
    output: list[str] | None = None

    @classmethod
    async def collect(cls, device: Device) -> "TechSupport":
        output = io.StringIO()
        async for out in device.stream("show techsupport --silent"):
            output.write(out)
        output.seek(0)
        lines = output.readlines()

        return cls(path=lines[-1].strip(), output=lines)
