from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dev_db_user: str = "ngcplus"
    dev_db_password: str = ""
    dev_db_dsn: str = "10.0.39.231:1521/DEVTNRPT_NGCPLUS_PDB1_1"
    test_db_user: str = "ngcplus"
    test_db_password: str = ""
    test_db_dsn: str = "10.0.39.231:1521/TSTTNRPT_NGCPLUS_PDB1"

    ssh_host: str = "10.0.39.201"
    ssh_user: str = "ngcplus"
    ssh_key_path: str = "/keys/id"
    data_root: str = "/u01/ngcplus/DCH/DATA"
    ref_operator: str = "FRAF1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
