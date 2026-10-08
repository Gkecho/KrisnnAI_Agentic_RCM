import pytest

from krisnai.config import DbSettings


def test_missing_required_env_raises():
    with pytest.raises(RuntimeError, match="KRISNAI_DB_SERVER"):
        DbSettings.from_env({})


def test_trusted_connection_when_no_user():
    s = DbSettings.from_env({"KRISNAI_DB_SERVER": "srv", "KRISNAI_DB_NAME": "db"})
    assert s.trusted
    assert "Trusted_Connection=yes" in s.odbc_connect_string()
    assert "PWD" not in s.odbc_connect_string()


def test_sql_auth_url():
    s = DbSettings.from_env(
        {
            "KRISNAI_DB_SERVER": "srv",
            "KRISNAI_DB_NAME": "db",
            "KRISNAI_DB_USER": "u",
            "KRISNAI_DB_PASSWORD": "p@ss;word",
            "KRISNAI_DB_TRUST_CERT": "true",
        }
    )
    assert not s.trusted
    assert s.sqlalchemy_url().startswith("mssql+pyodbc:///?odbc_connect=")
    assert "TrustServerCertificate" in s.odbc_connect_string()
