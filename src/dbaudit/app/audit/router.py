import logging

import jsondiff
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from app.audit.config import AppConfig
from app.audit.database import (
    get_audit_db_client,
    setup_collections,
    validate_collection,
)
from app.audit.enums import OperationType
from app.audit.models import (
    Auditlog,
    AuditlogCreateRequest,
    AuditlogSearchRequest,
    AuditlogSearchResult,
)
from app.audit.service import (
    insert_new_auditlog,
    structure_changes,
    query_previous_log,
)
from app.audit.utils import get_current_datetime, oid


router = APIRouter(prefix="/auditlogs", tags=["auditlogs"])

logger = logging.getLogger(__name__)


# Startup event to set up the audit DB before making the service live.
@router.on_event("startup")
async def startup():
    await setup_collections()


# Method to inject the audit database as a dependency for incoming requests.
def get_db() -> AsyncIOMotorDatabase:
    return get_audit_db_client()[AppConfig.AUDIT_DB_NAME]


@router.post(
    "",
    summary="Create an audit log for a tracked entity.",
    response_description="The newly created auditlog document.",
    response_model=Auditlog,
    response_model_by_alias=False,
)
async def create_auditlog(
    request: AuditlogCreateRequest = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Only documents from valid collections in source DB will be audited.
    if not validate_collection(request.collection):
        raise HTTPException(status_code=400, detail=f"Collection type {request.collection} is not supported.")

    # Extracting the mandatory auditlog fields.
    entity_id = oid(request.document["_id"])
    executed_at = request.document[AppConfig.EXECUTED_AT_FIELD_NAME]
    executed_by = oid(request.document[AppConfig.EXECUTED_BY_FIELD_NAME])

    # Determining the collection to insert into.
    collection = db[request.collection]

    # Determining the change type and what was modified using JsonDiff.
    try:
        latest_auditlog = await query_previous_log(collection, entity_id)

    except OperationFailure as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to query the latest log due to a DB issue, retrying may resolve the problem.",
        ) from e

    if latest_auditlog is None:
        operation_type = OperationType.INSERT
        changes = None
    
    else:
        raw_changes = jsondiff.diff(
            request.document,
            latest_auditlog["document"],
            syntax="symmetric",
        )

        try:
            changes = structure_changes(raw_changes)
            operation_type = OperationType.UPDATE if not changes else OperationType.DELETE

        except Exception as e:
            logger.exception(
                "An unexpected error occured while structuring identified changes.",
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail="Internal Server Error") from e

    # Configuring new record to be inserted into audit trail.
    auditlog = Auditlog(
        collection=request.collection,
        entity_id=entity_id,
        operation_type=operation_type,
        executed_at=executed_at,
        executed_by=executed_by,
        document=request.document,
        changes=jsonable_encoder(changes),
        created_at=get_current_datetime(),
    )

    try:
        await insert_new_auditlog(collection, auditlog)

    except OperationFailure as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to insert the auditlog due to a DB issue, retrying may resolve the problem.",
        ) from e

    return auditlog


@router.get(
    "",
    summary="Search for auditlogs.",
    response_description="List of audit records matching the search criteria.",
    response_model=AuditlogSearchResult,
)
async def search_auditlogs(
    request: AuditlogSearchRequest = Depends(AuditlogSearchRequest),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Validating target collection.
    if not validate_collection(request.collection):
        raise HTTPException(
            status_code=400,
            detail=f"Collection type {request.collection} is not supported",
        )
    
    # One of resource ID or user ID must be provided.
    if not request.entity_id and not request.user_id:
        raise HTTPException(
            status_code=400, detail="Entity ID or user ID must be provided."
        )

    criteria = request.get_criteria()
    sort_order = -1 if request.order == "desc" else 1

    logs = (
        await db[request.collection]
        .find(criteria)
        .skip(request.offset)
        .sort(request.sort_by, sort_order)
        .to_list(length=request.limit)
    )

    total_count = await db[request.collection].count_documents(criteria)

    return AuditlogSearchResult(logs=logs, total_count=total_count)
