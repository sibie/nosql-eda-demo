from enum import Enum


# Enum with operation types that can be observed in a change event.
class OperationType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
