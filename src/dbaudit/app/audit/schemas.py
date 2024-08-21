from typing import Any

from bson.objectid import ObjectId
from pydantic import BaseModel, Field


# Mongo ObjectId wrapper for Pydantic models.
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


# Represents a change to a field value in a document.
class FieldChange(BaseModel):
    new_value: Any = Field(...)
    old_value: Any = Field(...)


# Represents a change to a list element in a document.
class ListChange(BaseModel):
    index: Any = Field(...)
    item: Any = Field(...)


# Represents a warning identified during change event inspection.
class Warning(BaseModel):
    type: str = Field(...)
    description: str = Field(...)
