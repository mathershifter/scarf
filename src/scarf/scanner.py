import asyncio
import socket
import time
from collections.abc import AsyncIterator
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_network

import asyncssh
from pydantic import BaseModel, RootModel

from scarf.device import AuthHandler, Device

# log = structlog.get_logger()

sem = asyncio.Semaphore(100)

AnyIPNetwork = IPv4Network | IPv6Network
AnyIPAddress = IPv4Address | IPv6Address
AnyHostAddress = AnyIPAddress | AnyIPNetwork | str


async def _check_ssh(ip: AnyIPAddress):
    async with sem:
        try:
            conn = await asyncio.wait_for(
                asyncssh.connect(str(ip), known_hosts=None), timeout=10.0
            )
            conn.close()
        except asyncssh.PermissionDenied:
            pass
        except (OSError, asyncssh.Error):
            return ip, False

        return ip, True


class Network(BaseModel):
    netaddr: AnyIPNetwork
    hostname: str | None = None

    @classmethod
    def from_address(cls, addr: AnyHostAddress) -> "Network":
        hostname: str | None = None
        network: AnyIPNetwork
        if isinstance(addr, str):
            try:
                network = ip_network(addr, strict=False)
            except ValueError:
                hostname = addr
                resolved = socket.getaddrinfo(str(addr), None, socket.AF_INET)
                network = ip_network(resolved[0][4][0], strict=False)
        elif isinstance(addr, AnyIPAddress):
            network = ip_network(addr, strict=False)

        return cls(netaddr=network, hostname=hostname)


class Networks(RootModel):
    root: list[Network]

    @classmethod
    def from_addresses(cls, addrs: list[AnyHostAddress]) -> "Networks":
        return cls(root=[Network.from_address(addr) for addr in addrs])


class SentinelDevice(Device):
    def __init__(self, target: str):
        super().__init__(target, auth=None)
        self._serial = "sentinel"


class Scanner:
    def __init__(
        self,
        networks: list[AnyHostAddress],
        auth: AuthHandler | tuple[str, str],
        auto_connect: bool = True,
    ):
        # Resolve the network and hostname, if needed. hostname is None if the network is a valid IP.
        self._netaddrs = Networks.from_addresses(networks)
        self._auth = auth
        self._auto_connect = auto_connect

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def _hosts(self) -> AsyncIterator[AnyIPAddress]:
        # Sort networks by prefix length, so that smaller networks are scanned first.
        sorted_networks = sorted(self._netaddrs.root, key=lambda x: x.netaddr.prefixlen)
        for network in sorted_networks:
            for host in network.netaddr.hosts():
                yield host

    async def scan(self, rate: int = 10, count: int | None = None) -> AsyncIterator["Device"]:
        seen: set[str] = set()
        consecutive_failures: dict[str, int] = {}
        interations = 0
        while True:  # Continuous scanning loop
            start_time = time.time()
            tasks = [_check_ssh(ip) async for ip in self._hosts()]
            results = await asyncio.gather(*tasks)

            for ip, is_up in results:
                ip_str = str(ip)
                if is_up:
                    if ip_str not in seen:
                        device = Device(ip_str, auth=self._auth)
                        if self._auto_connect:
                            try:
                                await device.connect()
                            except (OSError, asyncssh.Error):
                                # log.warning(
                                #     "scan", msg=f"Failed to connect to {ip}, skipping"
                                # )
                                continue
                        seen.add(ip_str)
                        yield device
                    consecutive_failures.pop(ip_str, None)  # clear on success
                else:
                    if ip_str in seen:
                        consecutive_failures[ip_str] = (
                            consecutive_failures.get(ip_str, 0) + 1
                        )
                        if consecutive_failures[ip_str] >= 3:
                            seen.discard(ip_str)
                            del consecutive_failures[ip_str]
                            yield SentinelDevice(ip_str)
            sleep_time = rate - (time.time() - start_time)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            if count is not None:
                interations += 1
                if interations >= count:
                    break

    async def scan_once(self) -> list["Device"]:
        """Perform a single scan pass and return all discovered devices.

        Unlike ``scan()``, this does not loop.  Devices are returned without
        an active SSH connection; the caller is responsible for connecting.
        """
        ssh_tasks = [_check_ssh(ip) async for ip in self._hosts()]
        results = await asyncio.gather(*ssh_tasks)
        devices = []
        for ip, is_up in results:
            if is_up:
                devices.append(Device(str(ip), auth=self._auth))
        return devices
