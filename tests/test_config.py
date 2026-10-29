import pytest

from krisnnai.config import DbSettings


def test_missing_required_env_raises():
    with pytest.raises(RuntimeError, match="KRISNNAI_DB_SERVER"):
        DbSettings.from_env({})


def test_trusted_connection_when_no_user():
    s = DbSettings.from_env({"KRISNNAI_DB_SERVER": "srv", "KRISNNAI_DB_NAME": "db"})
    assert s.trusted
    assert "Trusted_Connection=yes" in s.odbc_connect_string()
    assert "PWD" not in s.odbc_connect_string()


def test_sql_auth_url():
    s = DbSettings.from_env(
        {
            "KRISNNAI_DB_SERVER": "srv",
            "KRISNNAI_DB_NAME": "db",
            "KRISNNAI_DB_USER": "u",
            "KRISNNAI_DB_PASSWORD": "p@ss;word",
            "KRISNNAI_DB_TRUST_CERT": "true",
        }
    )
    assert not s.trusted
    assert s.sqlalchemy_url().startswith("mssql+pyodbc:///?odbc_connect=")
    assert "TrustServerCertificate" in s.odbc_connect_string()
