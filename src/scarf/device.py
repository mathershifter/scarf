import asyncio
import enum
import fcntl
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import asyncssh

from scarf.drivers import Driver, from_device

BytesOrStr = bytes | str


class DeviceError(Exception):
    pass


class ConnectionError(DeviceError):
    pass


class StreamError(DeviceError):
    pass


class RunError(DeviceError):
    pass


class AuthMethod(enum.StrEnum):
    PASSWORD = "password"
    PUBLICKEY = "publickey"
    KEYBOARDINTERACTIVE = "keyboard-interactive"
    HOSTBASED = "hostbased"
    GSSAPI_KEYEX = "gssapi-keyex"
    GSSAPI_WITH_MIC = "gssapi-with-mic"
    NONE = "none"

@dataclass
class AuthHandler:
    """Base class for authentication handlers."""

    def get_auth_kwargs(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class PasswordHandler(AuthHandler):
    """Password authentication handler."""
    username: str
    password: str

@dataclass
class PublicKeyHandler(AuthHandler):
    """Private key authentication handler."""

    username: str
    client_keys: list[str]
    passphrase: str | None = None


class DeviceLocked(Exception):
    pass


def lock_file(identifier: str, lock_dir: Path) -> Path:
    """Return the Path to the .lock file for this device serial."""
    return Path(lock_dir) / f"{identifier}.lock"


@contextmanager
def device_lock(device: "Device", lock_dir: Path):
    """Exclusive per-device lock. Raises DeviceLocked if already held."""
    path = lock_file(device.target, lock_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise DeviceLocked(
                f"Device {device.target} is locked — another command may be running"
            )
        try:
            fd.write(str(os.getpid()))
            fd.flush()
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)


class Device:
    """Async SSH device backed by asyncssh.

    Use the async context manager ``async with Device(...) as device:`` to
    ensure the connection is closed when done.
    """

    def __init__(
        self,
        target: str,
        auth: AuthHandler | tuple[str, str] | None = None,
        # driver: Driver | None = None,
        context: str | None = None,
        timeout: int = 10,
    ):
        self._driver: Driver | None = None
        self._target = target
        self._auth = self._handle_auth(auth) or PasswordHandler(username="", password="")
        self._timeout = timeout
        self._context: str | None = str(context) if context else None

        # Populated by connect() / create()
        self._conn: asyncssh.SSHClientConnection | None = None
        self._serial: str | None = None
        self._prompt: str = ""
        # self._log = log.bind(target=target)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self) -> None:
        """Open the SSH connection and bootstrap the device state."""

        self._conn = await asyncio.wait_for(
            asyncssh.connect(
                self._target,
                known_hosts=None,
                **self._auth.get_auth_kwargs(),
            ),
            timeout=self._timeout,
        )

        self._driver = await self._get_driver()

        # self._log.info("connected")

    async def close(self) -> None:
        """Close the SSH connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


    async def _get_driver(self) -> Driver | None:
        if self._driver is not None:
            return self._driver

        return await from_device(self)  # type: ignore[arg-type]


    def _prefixed(self, cmd: str) -> str:
        """Prepend workspace cd so every command runs in the right directory.

        We cannot rely on asyncssh's ``cwd`` parameter (not always supported
        on network devices), so we prefix every command explicitly.
        """
        if not self._context:
            return cmd

        return f"cd {self._context} && {cmd}"


    def _handle_auth(self, auth: AuthHandler | tuple[str, str] | None) -> AuthHandler | None:
        if isinstance(auth, tuple):
            return PasswordHandler(username=auth[0], password=auth[1])
        return auth

    @asynccontextmanager
    async def context(self, context: str = ""):
        """Change the working directory for a block of commands."""
        _saved_context = self._context

        if context:
            self._context = context

        try:
            yield
        finally:
            self._context = _saved_context

    async def run(self, cmd: str) -> tuple[int, BytesOrStr, BytesOrStr]:
        """Run *cmd* in the workspace directory and return stdout."""
        assert self._conn is not None, "not connected"

        cmd = self._prefixed(cmd)

        result = await self._conn.run(cmd)

        if isinstance(result.stdout, bytes):
            result.stdout = result.stdout.decode("utf-8")

        if isinstance(result.stderr, bytes):
            result.stderr = result.stderr.decode("utf-8")

        if result.exit_status is None:
            raise ConnectionError("Command failed, connection closed.")

        if result.stderr is None:
            result.stderr = ""

        if result.stdout is None:
            result.stdout = ""

        # if result.stdout:
        #     for line in result.stdout.splitlines():
        #         self._log.info("run", line=line, cmd=cmd)
        # result.stdout
        # result.stderr
        return result.exit_status, result.stdout, result.stderr

    async def stream(self, cmd: str) -> AsyncIterator[str]:
        """Run *cmd* and yield stdout lines as they arrive. Raises StreamError on non-zero exit."""
        assert self._conn is not None, "not connected"

        cmd = self._prefixed(cmd)

        async with self._conn.create_process(cmd) as process:
            async for line in process.stdout:
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                stripped = line.rstrip("\n")
                # self._log.info("stream", line=stripped, cmd=cmd)
                yield stripped

            complete = await process.wait()
            
            err = complete.stderr or ""
            if isinstance(err, bytes):
                err = err.decode("utf-8")

            if complete.exit_status != 0:
                raise StreamError(
                    f"Command failed, connection closed: {complete.exit_status} {err}"
                )

    async def send_command(self, cmd: str) -> BytesOrStr:
        """Run *cmd* in the workspace directory and return stdout."""
        async with self.context():
            status, out, err = await self.run(cmd)
        if status != 0:
            raise RunError(f"Command returned non-zero status: {status} {err}")

        return out

    async def stream_command(self, cmd: str) -> AsyncIterator[str]:
        """Run *cmd* in the workspace directory and yield stdout lines.

        Convenience wrapper that applies the workspace prefix — symmetric with
        send_command(). Use stream() directly for commands that must not be
        workspace-prefixed.
        """
        async with self.context():
            async for line in self.stream(cmd):
                yield line

    @property
    def conn(self) -> asyncssh.SSHClientConnection:
        """Raw asyncssh connection, used by asyncssh.scp callers."""
        assert self._conn is not None, "not connected"
        return self._conn

    @property
    def driver(self) -> Driver | None:
        return self._driver

    @property
    def serial(self) -> str:
        return self._driver.serial_number if self._driver else "(unknown)"

    @property
    def target(self) -> str:
        return self._target

    @property
    def prompt(self) -> str:
        return self._prompt

    @property
    def hostname(self) -> str:
        return self._driver.hostname if self._driver else "(unknown)"
