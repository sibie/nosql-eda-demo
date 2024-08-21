import logging
from typing import List

import jsondiff
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import OperationFailure
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.audit.enums import OperationType, WarningType
from app.audit.models import Auditlog
from app.audit.schemas import FieldChange, ListChange, PyObjectId


logger = logging.getLogger(__name__)


# Method to get the previous audit log for a given entity ID, if it exists.
@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(OperationFailure),
    wait=wait_fixed(1),
)
async def query_latest_log(
    collection: AsyncIOMotorCollection,
    entity_id: PyObjectId,
):
    # Query the latest audit log with the entity ID provided if it exists, None if not.
    try:
        result = (
            await collection.find({"entity_id": entity_id})
            .sort("executed_at", -1)
            .to_list(length=1)
        )

    # Retry logic kicks in if we encounter DB operation exceptions.
    except OperationFailure:
        logger.exception(f"Failed to query the latest auditlog of entity {str(entity_id)}.", exc_info=True)
        raise

    return result[0] if result else None


# Method to structure changes identified by Jsondiff into a consistent format.
def structure_changes(raw_data):
    changes = {}

    for key, value in raw_data.items():
        # Insertion & Deletion of non-dictionary items into a list field.
        # Eg -> 'tags': {insert: [(1, 'unavailable')], delete: [(1, 'discount')]}
        if key == jsondiff.symbols.insert:
            changes["deletes"] = [
                ListChange(index=list_value[0], item=list_value[1])
                for list_value in value
            ]

        elif key == jsondiff.symbols.delete:
            changes["inserts"] = [
                ListChange(index=list_value[0], item=list_value[1])
                for list_value in value
            ]

        elif isinstance(value, list):
            # Value change for a standard field.
            # Eg -> 'price': [299.99, 349.99]
            changes[str(key)] = FieldChange(new_value=value[0], old_value=value[1])

        elif isinstance(value, dict):
            # Using recursion to handle nested fields.
            changes[str(key)] = structure_changes(value)

        else:
            raise HTTPException(status_code=500, detail="Unknown change type.")

    return changes


# Method to inspect the auditlog for any custom warnings we want to document.
# Keeping this in a separate file to avoid cluttering models.py. The number of
# checks could be extensive, especially if we have a large number of collections.

def run_inspection(latest_log: Auditlog) -> List[WarningType]:
    warnings: List[WarningType] = []
    
    # In case a resource that was previously marked as deleted is reintroduced in the DB.
    if latest_log and latest_log.operation_type == OperationType.DELETE:
        warnings.append(WarningType.RESOURCE_ACCESS_AFTER_DELETE.format())
    
    # Like above, we can add any standard checks here that are applicable to all collections.

    # In case of collection-specific checks, we could go for a flexible design.
    # For example, lets say we want to check the comments collection documents
    # for possible spam and blog_posts collection documents for profane language.
    # Simple pseudo-code example below:
    #
    # def inspect_comments():
    #     warnings: List[WarningType] = []
    #     if log.check_for_spam():
    #         warnings.append(WarningType.SPAM_WARNING.format())
    #     return warnings
    #
    # def inspect_blog_posts():
    #     warnings: List[WarningType] = []
    #     if log.check_for_profanity():
    #         warnings.append(WarningType.PROFANITY_WARNING.format())
    #     return warnings
    #
    # inspection_factory: Dict[str, List[WarningType]] = {
    #     "comments": inspect_comments(),
    #     "blog_posts": inspect_blog_posts(),
    # }
    #
    # warnings.extend(inspection_factory.get(latest_log.collection))

    return warnings


# Method to insert an auditlog into collection.
@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(OperationFailure),
    wait=wait_fixed(1),
)
async def insert_new_auditlog(collection: AsyncIOMotorCollection, auditlog: Auditlog):
    try:
        await collection.insert_one(auditlog.__dict__)

    # Retry logic kicks in if we encounter DB operation exceptions.
    except OperationFailure:
        logger.exception(f"Failed to insert auditlog for entity {auditlog.entity_id}.", exc_info=True)
        raise
