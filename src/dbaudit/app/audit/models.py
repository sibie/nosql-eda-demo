from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from bson.objectid import ObjectId
from fastapi import Query
from pydantic import BaseModel, Field, root_validator

from app.audit.config import AppConfig
from app.audit.enums import OperationType
from app.audit.schemas import PyObjectId, Warning
from app.audit.utils import oid


# Model class for an auditlog describing a change made to an entity of interest.
class Auditlog(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    collection: str = Field(...)
    entity_id: PyObjectId = Field(...)
    operation_type: OperationType = Field(...)
    executed_at: datetime = Field(...)
    executed_by: PyObjectId = Field(...)
    document: Dict = Field(...)
    changes: Optional[Dict] = Field(default_factory=dict)
    warnings: Optional[List] = Field(default_factory=list)
    created_at: datetime = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        min_anystr_length = 1
        schema_extra = {
            "example": {
                "collection": "products",
                "entity_id": "66c20e3c694961369471f149",
                "operation_type": OperationType.UPDATE,
                "executed_at": "2024-08-08T10:00:40.250000",
                "executed_by": "66c20e5e5fca873b5e31a51d",
                "document": {
                    "_id": "66c20e3c694961369471f149",
                    "name": "Alienware m18 R2 Gaming Laptop",
                    "price": 1899.99,
                    "last_updated_at": "2024-08-08T10:00:40.250000",
                    "last_updated_by": "66c20e5e5fca873b5e31a51d",
                },
                "changes": {
                    "price": [1899.99, 1999.99], # [new_value, old_value]
                    "last_updated_at": [
                        "2024-08-08T10:00:40.250000",
                        "2023-08-08T10:00:40.250000",
                    ],
                },
                "warnings": [],
                "created_at": "2024-08-08T10:01:40.250000",
            }
        }


# Request schema to create a new auditlog.
class AuditlogCreateRequest(BaseModel):
    collection: str = Field(...)
    document: Dict = Field(...)

    @root_validator
    def validate_document(cls, v):
        collection = v.get("collection")
        document = v.get("document")

        if collection is not None and document is not None:
            if "_id" not in document.keys():
                raise ValueError("Entity must have a valid ID.")

            elif (
                AppConfig.EXECUTED_AT_FIELD_NAME not in document.keys()
                or document[AppConfig.EXECUTED_AT_FIELD_NAME] is None
            ):
                raise ValueError("The date and time of the change is missing.")

            elif (
                AppConfig.EXECUTED_BY_FIELD_NAME not in document.keys()
                or document[AppConfig.EXECUTED_BY_FIELD_NAME] is None
            ):
                raise ValueError("The ID of the user responsible for the change is missing.")
        
        return v

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "collection": "products",
                "document": {
                    "_id": "66c20e3c694961369471f149",
                    "name": "Alienware m18 R2 Gaming Laptop",
                    "price": 1899.99,
                    "last_updated_at": "2024-08-08T10:00:40.250000",
                    "last_updated_by": "66c20e5e5fca873b5e31a51d",
                },
            },
        }


# Request schema to for an audit search.
class AuditlogSearchRequest(BaseModel):
    # Query parameters.
    collection: str = Field(...)
    entity_id: Optional[str]
    user_id: Optional[str]
    operation_type: Optional[OperationType]
    start_date: Optional[datetime]
    end_date: Optional[datetime]

    # Query options.
    offset: int = 0
    sort_by: Literal["executed_at"] = "executed_at"
    order: Literal["asc", "desc"] = "desc"
    limit: int = Query(default=100, le=1000, ge=0)

    def get_criteria(self):
        criteria: Dict[str, Any] = {}

        # Filter by entity ID.
        if self.entity_id:
            criteria["entity_id"] = oid(self.entity_id)

        # Filter by user ID, i.e. the one responsibile for the change.
        if self.user_id:
            criteria["executed_by"] = oid(self.user_id)
        
        # Filter by operation type.
        if self.operation_type:
            criteria["operation_type"] = self.operation_type.value
        
        # Filter by date range.
        if self.start_date:
            criteria["executed_at"] = {"$gte": self.start_date}

        if self.end_date:
            criteria["executed_at"] = {"$lte": self.end_date}

        return criteria


# Response model for audit trail search queries.
class AuditlogSearchResult(BaseModel):
    logs: List[Auditlog] = Field(...)
    total_count: int = Field(...)

    class Config:
        json_encoders = {ObjectId: str}
