import re
from typing import Any, Callable

from pydantic import BaseModel, RootModel, model_validator
import numpy as np
from scarf.drivers.interfaces import Device
from scarf.utils import snake_case


class AsicTemperature(BaseModel):
    sensor: int
    location: str
    current: float
    hist_min: float
    hist_max: float

    def z_score(self, mean: float, stddev: float) -> float:
        if stddev == 0.0:
            return 0.0
        return (self.current - mean) / stddev


class AsicTemperatures(RootModel):
    root: list[AsicTemperature]

    @model_validator(mode="before")
    @classmethod
    def transform_keys(cls, data: list[tuple[str, float]]) -> Any:
        data_arr = [("", 0.0)] * len(data)
        for k, v in data:
            # extract index from key
            idx, sensor = re.sub(r"(.*)\((\d+)\)", r"\2 \1", k).split(" ")
            data_arr[int(idx)] = (sensor, float(v))

        return data_arr

    @classmethod
    async def collect(cls, device: Device) -> "AsicTemperatures":
        status, out, err = await device.run("bcmcmd \"dsh -c 'hmon temp'\"")
        if status != 0:
            raise ValueError(f"Failed to collect asic temperature: {err}")

        data = _parse_asic_temperature(out)
        return cls([AsicTemperature(**item) for item in data])

    def filter(
        self, predicate: Callable[[AsicTemperature], bool]
    ) -> "AsicTemperatures":
        return AsicTemperatures([s for s in self.root if predicate(s)])

    def topn(self, n: int = 8) -> "AsicTemperatures":
        return AsicTemperatures(
            sorted(self.root, key=lambda item: item.current, reverse=True)[:n]
        )

    def get_sensor_temperature(self, sensor: str) -> float | None:
        for s in self.root:
            if s.sensor == sensor:
                return s.current
        return None

    @property
    def currents(self) -> list[float]:
        return [s.current for s in self.root]

    temperatures = currents

    @property
    def sensors(self) -> list[str]:
        return [s.location for s in self.root]

    @property
    def serdes(self) -> "AsicTemperatures":
        """Return only serdes sensors"""
        return self.filter(
            lambda s: s.location.startswith("pm") and not s.location.startswith("pm_")
        )

    @property
    def _asarray(self) -> np.ndarray:
        return np.array([v for _, v in self.root])

    @property
    def mean(self) -> float:
        return float(np.mean(self._asarray))

    @property
    def median(self) -> float:
        return np.median(self._asarray)

    @property
    def stddev(self) -> float:
        return float(np.std(self._asarray))

    @property
    def z_scores(self) -> list[float]:
        if self.stddev == 0.0:
            return [0.0] * len(self.root)
        return [s.z_score(self.mean, self.stddev) for s in self.root]

    @property
    def mad(self) -> float:
        return float(np.mean(np.abs(self._asarray - self.mean)))


def _parse_asic_temperature(data):
    """Parse ASIC temperature sensor data from bcmcmd output

    Args:
        temp_output: Output from bcmcmd "dsh -c 'hmon temp'"

    Returns:
        dict: Dictionary of sensor_key -> temperature (float)

    Sample output:
    Sensor ID       Current         Hist Min        Hist Max        Location
    0               53.1            50.2            55.5            top.pvtmon0
    1               54.8            52.5            57.4            top.pvtmon1
    2               56.4            54.1            59.4            top.pvtmon2
    3               54.8            52.2            57.4            top.pvtmon3
    4               49.9            47.5            52.5            top.pvtmon4
    5               50.8            48.2            53.5            top.pvtmon5
    6               53.5            50.8            56.1            top.pvtmon6
    7               54.1            51.5            56.8            top.pvtmon7
    8               52.8            50.2            55.5            top.pvtmon8
    9               50.5            47.9            53.1            top.pvtmon9
    10              47.9            45.2            50.5            top.pvtmon10
    11              50.5            47.9            53.1            top.pvtmon11
    12              50.5            47.5            52.8            top.pvtmon12
    13              51.2            48.5            53.8            top.pvtmon13
    14              49.9            47.2            52.5            pm_mgmt
    15              50.8            0.0             53.5            pm0
    16              53.1            0.0             56.1            pm1
    17              51.8            0.0             54.5            pm2
    18              51.2            0.0             53.8            pm3
    19              53.1            0.0             55.5            pm4
    20              55.1            0.0             57.8            pm5
    """
    temps = []
    fields = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        if "Sensor ID" in line:
            fields = [snake_case(f) for f in line.split()]
            continue

        if len(fields) == 0:
            continue

        parts = line.split()

        if len(parts) < len(fields):
            continue
        data = dict(zip(fields, parts))
        temps.append(
            {
                "sensor": int(data["sensor_id"]),
                "location": data["location"],
                "current": float(data["current"]),
                "hist_min": float(data["hist_min"]),
                "hist_max": float(data["hist_max"]),
            }
        )

    return temps
