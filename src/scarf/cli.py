import asyncio
from importlib.metadata import version
from pathlib import Path

import asyncssh
import click
import rich
from rich.console import Console

from scarf.device import AuthHandler, Device
from scarf.scanner import Scanner, SentinelDevice
from scarf.settings import Settings

console = Console(log_path=False)
settings = Settings()

@click.group()
@click.version_option(version("scarf"), "-v", "--version")
@click.option(
    "-t",
    "--target",
    required=False,
    multiple=True,
    default=(),
    help="Hostname, IP address or IP network to scan for target devices (may be repeated)",
)
@click.option(
    "--username",
    "-l",
    default=settings.username,
    show_default=True,
    help="SSH username",
)
@click.option(
    "--password",
    "-p",
    default=settings.password,
    show_default=False,
    help="SSH password",
)
@click.option(
    "--lock-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default=settings.lock_dir,
    show_default=True,
    help="Directory to store per-device lock files",
)
@click.option(
    "--log-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    default=settings.log_dir,
    show_default=True,
    help="Directory to store log files",
)
@click.pass_context
def cli(
    ctx, target, username, password, log_dir, lock_dir
) -> None:
    ctx.ensure_object(Settings)

    settings.username = username
    settings.password = password
    settings.log_dir = Path(log_dir)
    settings.targets = list(target)
    settings.lock_dir = Path(lock_dir)

    log_dir.mkdir(exist_ok=True)

    ctx.obj = settings

def _dispatch(
    targets, auth: AuthHandler | tuple[str, str], body, count: int | None = None
) -> None:
    """Continuously scan until Ctrl+C, running body(device, prefix) once per new device."""

    scanner = Scanner(targets, auth=auth, auto_connect=False)
    pending: set[asyncio.Task] = set()

    async def _connect_and_run(candidate: Device) -> None:
        console.log(f"[cyan]Found {candidate.target}, attempting connection...[/cyan]")
        try:
            await candidate.connect()

        # except (OSError, asyncssh.Error) as exc:
        #     sys.exit('SSH connection failed: ' + str(exc))
        except (OSError, asyncssh.Error) as exc:
            console.log(
                f"[yellow]Could not connect to {candidate.target}: {exc}[/yellow]"
            )
            return
        console.log(f"[green]Connected to {candidate.target}[/green]")
        prefix = f"[dim]{candidate.hostname}[/dim] "
        await body(candidate, prefix)

    async def _cleanup():
        console.log(
            "[yellow]Scan stopped. Waiting for in-flight tasks to finish...[/yellow]"
        )
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _run():
        try:
            # iterations = 0
            async for candidate in scanner.scan(count=count):
                if isinstance(candidate, SentinelDevice):
                    console.log(f"[red]Lost {candidate.target}[/red]")
                    continue
                task = asyncio.create_task(_connect_and_run(candidate))
                pending.add(task)
                task.add_done_callback(pending.discard)

        except KeyboardInterrupt:
            # await _cleanup()
            console.log("\n[yellow]Interrupted.[/yellow]")
        except asyncio.CancelledError:
            # await _cleanup()
            ("[yellow]Done.[/yellow]")
        finally:
            await _cleanup()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def info(ctx):
    """Print device info."""

    async def _body(device: Device, prefix: str) -> None:
        rich.print(f"{prefix}{device.driver}")

    _dispatch(ctx.obj.targets, auth=ctx.obj.auth, body=_body, count=1)


@cli.command()
@click.pass_context
@click.option(
    "-r",
    "--rate",
    type=int,
    default=10,
    show_default=True,
    help="Seconds between scan rounds",
)
def scan(ctx, subnet, rate):
    """Continuously scan a targets for SSH-accessible hosts and print each discovered IP."""

    async def _run():
        scanner = Scanner(ctx.obj["targets"], auth=ctx.obj.auth, auto_connect=False)
        async for device in scanner.scan(rate):
            console.log(f"[bold green]Found {device.target}[/bold green]")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.log("\n[yellow]Interrupted.[/yellow]")

@cli.command()
@click.argument("command", nargs=-1)
@click.pass_context
def run(ctx, command):
    """Execute an arbitrary command on the device and stream output."""

    async def _body(device: Device, prefix: str) -> None:
        try:
            async for line in device.stream(" ".join(command)):
                # console.log(f"{prefix}{line}")
                rich.print(f"{prefix}{line}")
        except asyncssh.ChannelOpenError as exc:
            console.log(f"[red]Error occurred while running command on {device.target}: {exc}[/red]")

    _dispatch(ctx.obj.targets, auth=ctx.obj.auth, body=_body, count=1)

def main():
    try:
        cli()
    except KeyboardInterrupt:
        console.log("\n[yellow]Interrupted.[/yellow]")


if __name__ == "__main__":
    main()
