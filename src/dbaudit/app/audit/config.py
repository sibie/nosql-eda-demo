import os


# We are assuming here that source DB is separate from the audit DB for simplicity.
class AppConfig:
    # Connection details of the audit DB
    AUDIT_DB_CONNECTION_STRING = "AUDIT_DB_CONNECTION_STRING"
    AUDIT_DB_NAME = os.environ.get("AUDIT_DB_NAME")
    
    # Local audit DB instance used for development.
    DB_DEV = "mongodb://localhost:27017"

    # Connection details of the source API DB to be audited.
    API_DB_CONNECTION_STRING = os.environ.get("API_DB_CONNECTION_STRING")
    API_DB_NAME = os.environ.get("API_DB_NAME")

    # For every auditlog, we need to know who made the change and when the operation was done.
    # Here we can define the field name used in our source collections, so audit endpoints
    # can extract the required details from incoming requests.
    EXECUTED_AT_FIELD_NAME = os.environ.get("EXECUTED_AT_FIELD_NAME", "last_updated_at")
    EXECUTED_BY_FIELD_NAME = os.environ.get("EXECUTED_BY_FIELD_NAME", "last_updated_by")
    