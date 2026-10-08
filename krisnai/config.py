"""Runtime configuration from environment variables. No secrets live in the repo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class DbSettings:
    server: str
    database: str
    user: str | None = None
    password: str | None = None
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_server_certificate: bool = False

    @property
    def trusted(self) -> bool:
        """Windows integrated auth when no user is given."""
        return not self.user

    def odbc_connect_string(self) -> str:
        parts = [
            f"DRIVER={{{self.driver}}}",
            f"SERVER={self.server}",
            f"DATABASE={self.database}",
        ]
        if self.trusted:
            parts.append("Trusted_Connection=yes")
        else:
            parts += [f"UID={self.user}", f"PWD={self.password or ''}"]
        if self.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)

    def sqlalchemy_url(self) -> str:
        return "mssql+pyodbc:///?odbc_connect=" + quote_plus(self.odbc_connect_string())

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> DbSettings:
        env = os.environ if env is None else env
        missing = [k for k in ("KRISNAI_DB_SERVER", "KRISNAI_DB_NAME") if not env.get(k)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        return cls(
            server=env["KRISNAI_DB_SERVER"],
            database=env["KRISNAI_DB_NAME"],
            user=env.get("KRISNAI_DB_USER") or None,
            password=env.get("KRISNAI_DB_PASSWORD") or None,
            driver=env.get("KRISNAI_DB_DRIVER", "ODBC Driver 18 for SQL Server"),
            trust_server_certificate=env.get("KRISNAI_DB_TRUST_CERT", "").lower() in ("1", "true", "yes"),
        )
