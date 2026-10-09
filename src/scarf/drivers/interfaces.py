from collections.abc import AsyncIterator, Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")

BytesOrStr = bytes | str


class Device(Protocol):
    async def run(self, cmd: str) -> tuple[int, BytesOrStr, BytesOrStr]: ...
    def stream(self, cmd: str) -> AsyncIterator[BytesOrStr]: ...


class Verifier[T](Protocol):
    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]: ...


class Collector[T](Protocol):
    @classmethod
    async def collect(cls, device: Device) -> T: ...
