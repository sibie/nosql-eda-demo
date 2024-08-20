import os
from os.path import dirname, join

from dotenv import load_dotenv


# Function to load configuration details from .env.
def load_config() -> dict:
    dotenv_path = join(dirname(__file__), ".env")
    load_dotenv(dotenv_path)

    return {
        "API_DB_CONNECTION_STRING": os.getenv("API_DB_CONNECTION_STRING"),
        "API_DB_NAME": os.getenv("API_DB_NAME"),
        "AUDIT_DB_CONNECTION_STRING": os.getenv("AUDIT_DB_CONNECTION_STRING"),
        "AUDIT_DB_NAME": os.getenv("AUDIT_DB_NAME"),
        "TOKEN_COLLECTION": os.getenv("TOKEN_COLLECTION"),
        "AUDITLOG_ENDPOINT": os.getenv("AUDITLOG_ENDPOINT"),
        "EVENT_DOMAIN_ENDPOINT": os.getenv("EVENT_DOMAIN_ENDPOINT"),
        "FAILED_AUDITLOGS_TOPIC": os.getenv("FAILED_AUDITLOGS_TOPIC"),
    }


# Simple implementation as we only have 2 jobs.
def get_connection_str_by_job(config, job):
    return config["API_DB_CONNECTION_STRING"] if job == "audit" else config["AUDIT_DB_CONNECTION_STRING"]


# Simple implementation as we only have 2 jobs.
def get_db_name_by_job(config, job):
    return config["API_DB_NAME"] if job == "audit" else config["AUDIT_DB_NAME"]
