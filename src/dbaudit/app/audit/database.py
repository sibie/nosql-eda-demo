import os

import pymongo
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from app.audit.config import AppConfig


# Global var with audit DB client used for API operations.
_audit_db_client: AsyncIOMotorClient = None

# Fields to index for each audit collection.
_index_list = ["entity_id", "executed_at", "executed_by"]

# List of collections found in source DB.
_collections_list = []


# Method to reuse Audit DB client as a singleton.
def get_audit_db_client():
    global _audit_db_client
    
    if _audit_db_client is None:
        _audit_db_client = AsyncIOMotorClient(
            os.environ.get(
                AppConfig.AUDIT_DB_CONNECTION_STRING,
                AppConfig.DB_DEV,
            ),
            tz_aware=True,
        )

    return _audit_db_client


# Method to close Audit DB client.
async def close_audit_db_client():
    global _audit_db_client
    await _audit_db_client.close()
    _audit_db_client = None


# Method to create a collection in audit DB with required indexes.
async def create_collection(collection: AsyncIOMotorCollection):
    await collection.create_indexes([
        pymongo.IndexModel([(index, pymongo.ASCENDING)]) for index in _index_list
    ])


# Method to set up audit DB at router startup.
async def setup_collections():
    global _collections_list

    source_db_client = AsyncIOMotorClient(AppConfig.API_DB_CONNECTION_STRING)
    source_db: AsyncIOMotorDatabase = source_db_client[AppConfig.API_DB_NAME]
    _collections_list = await source_db.list_collection_names()
    source_db_client.close()

    audit_db: AsyncIOMotorDatabase = get_audit_db_client()[AppConfig.AUDIT_DB_NAME]
    for collection in _collections_list:
        await create_collection(audit_db[collection])


# Method to check if a collection type is supported by audit app.
def validate_collection(collection: str):
    return True if collection in _collections_list else False
