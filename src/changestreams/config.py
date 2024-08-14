import os
from os.path import dirname, join

from azure.appconfiguration.provider import (
    AzureAppConfigurationKeyVaultOptions,
    AzureAppConfigurationProvider,
    SettingSelector,
    load,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


AZ_APPCONFIG_ENDPOINT = os.getenv("CONFIG_ENDPOINT")


# Function to load stream configuration data from Azure App Config (or env if $RUN_ENV=LOCAL).
def load_config(label_filter: str = "\0") -> (dict | AzureAppConfigurationProvider):
    if os.getenv("RUN_ENV") == "LOCAL":
        return load_config_from_env()

    credential = DefaultAzureCredential(additionally_allowed_tenants=["*"])
    key_vault_options = AzureAppConfigurationKeyVaultOptions(credential=credential)

    # Retrieve config tagged with label_filter arg if provided, otherwise use "\0" -> (No Label).
    selects = [SettingSelector(key_filter="*", label_filter=label_filter)]

    return load(
        endpoint=AZ_APPCONFIG_ENDPOINT,
        credential=credential,
        key_vault_options=key_vault_options,
        selects=selects,
    )


# Function to load stream configuration data from the environment (during debugging).
def load_config_from_env() -> dict:
    dotenv_path = join(dirname(__file__), ".env")
    load_dotenv(dotenv_path)

    return {
        "DB_CONNECTION_STRING": os.getenv("DB_CONNECTION_STRING"),
        "DB_NAME": os.getenv("DB_NAME"),
        "TOKEN_COLLECTION": os.getenv("TOKEN_COLLECTION"),
        "AUDITLOG_ENDPOINT": os.getenv("AUDITLOG_ENDPOINT"),
        "EVENT_DOMAIN_ENDPOINT": os.getenv("EVENT_DOMAIN_ENDPOINT"),
        "FAILED_AUDITLOGS_TOPIC": os.getenv("FAILED_AUDITLOGS_TOPIC"),
    }
