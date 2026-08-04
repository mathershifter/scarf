import enum
import json
from typing import Iterable
from pydantic import BaseModel, RootModel, field_validator
from ahab.drivers.interfaces import Device
from ahab.drivers.helpers import _verify_helper


class Status(enum.StrEnum):
    running = "running"
    paused = "paused"
    restarting = "restarting"
    oom_killed = "oom_killed"
    dead = "dead"
    exited = "exited"


class ContainerState(BaseModel):
    status: Status
    exit_code: int
    error: str
    started_at: str
    finished_at: str

    def __bool__(self):
        return self.status == Status.running

    def __str__(self):
        return self.status


class DockerContainer(BaseModel):
    id: str
    name: str
    env: dict[str, str]
    state: ContainerState
    image: str
    networks: list[str]
    ports: list[str]
    mounts: list[tuple[str, str]]

    def verify(self) -> tuple[bool, str]:
        if self.state != "running":
            return False, f"{self.name} is not running"
        return True, f"{self.name} is running"

    @field_validator("name", mode="before")
    def _transform_name(cls, v: str) -> str:
        return v.lstrip("/")

    @field_validator("env", mode="before")
    def _transform_env(cls, v: list[str]) -> dict[str, str]:
        return {k: v for k, v in [e.split("=", maxsplit=1) for e in v]}

    @field_validator("mounts", mode="before")
    def _transform_mounts(cls, v: list[dict]) -> list[tuple[str, str]]:
        return [(m["Source"], m["Destination"]) for m in v]

    @field_validator("ports", mode="before")
    def _transform_ports(cls, v: dict[str, dict]) -> list[str]:
        return list(v.keys())

    @field_validator("networks", mode="before")
    def _transform_networks(cls, v: dict[str, dict]) -> list[str]:
        return list(v.keys())

    @field_validator("state", mode="before")
    def _transform_state(cls, v: ContainerState | dict) -> ContainerState:
        if isinstance(v, ContainerState):
            return v
        return ContainerState(
            status=Status[v["Status"]],
            exit_code=v["ExitCode"],
            error=v["Error"],
            started_at=v["StartedAt"],
            finished_at=v["FinishedAt"],
        )


class DockerContainers(RootModel):
    root: list[DockerContainer]

    @classmethod
    async def collect(cls, device: Device) -> "DockerContainers":

        status, out, err = await device.run(
            "docker inspect --format json $(docker ps -qa)"
        )
        if status != 0:
            raise ValueError(f"Failed to collect docker containers: {err}")
        containers = json.loads(out)

        return cls(
            [
                DockerContainer(
                    id=c["Id"],
                    name=c["Name"],
                    state=c["State"],
                    env=c["Config"]["Env"],
                    image=c["Image"],
                    networks=c["NetworkSettings"]["Networks"],
                    ports=c["Config"].get("ExposedPorts", {}),
                    mounts=c["Mounts"],
                )
                for c in containers
            ]
        )

    def verify(
        self, wanted: Iterable[tuple[str, str]] | None
    ) -> Iterable[tuple[bool, str, str]]:
        for ok, field, msg in _verify_helper(self, wanted):
            yield ok, field, msg


async def main():
    device = Device_("moby253")
    await device.connect()
    containers = await DockerContainers.collect(device)
    for c in containers.root:
        print(c.name, c.state.status)
    await device.close()


if __name__ == "__main__":
    import asyncio
    from ahab.device import Device as Device_

    asyncio.run(main())
