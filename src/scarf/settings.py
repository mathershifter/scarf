from pathlib import Path
from pydantic import Field
from tempfile import gettempdir
from pydantic_settings import BaseSettings

_base_dir = Path(__file__).parent.parent.resolve()
class Settings(BaseSettings):
    targets: list[str] = Field(validation_alias="SCARF_TARGETS", default=[])
    base_dir: Path = Field(validation_alias="SCARF_BASE_DIR", default=_base_dir)
    username: str = Field(validation_alias="SCARF_SSH_USERNAME", default="admin")
    password: str = Field(validation_alias="SCARF_SSH_PASSWORD", default="password")
    private_key: str = Field(validation_alias="SCARF_SSH_PRIVATE_KEY", default="")
    syslog_host: str = Field(validation_alias="SCARF_SYSLOG_HOST", default="localhost")
    syslog_port: int = Field(validation_alias="SCARF_SYSLOG_PORT", default=514)
    log_dir: Path = Field(validation_alias="SCARF_LOG_DIR", default=Path.cwd())
    lock_dir: Path = Field(validation_alias="SCARF_LOCK_DIR", default=Path(gettempdir()) / "scarf_locks")


    @property
    def auth(self) -> tuple[str, str] | None:
        if self.username and self.password:
            return (self.username, self.password)
        return None
