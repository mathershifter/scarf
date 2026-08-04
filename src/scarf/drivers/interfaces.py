from typing import Iterable, TypeVar, Protocol, AsyncIterator

T = TypeVar("T")


class Device(Protocol):
    async def run(self, cmd: str) -> tuple[int, str, str]: ...
    def stream(self, cmd: str) -> AsyncIterator[str]: ...


class Verifier[T](Protocol):
    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]: ...


class Collector[T](Protocol):
    @classmethod
    async def collect(cls, device: Device) -> T: ...
