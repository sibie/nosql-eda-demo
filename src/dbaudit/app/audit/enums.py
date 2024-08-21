from enum import Enum

from app.audit.schemas import Warning


# Enum with operation types that can be observed in a change event.
class OperationType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


# Enum with different warnings we want to inspect incoming change events for.
class WarningType(str, Enum):
    RESOURCE_ACCESS_AFTER_DELETE = "The latest log indicates the resource was deleted, despite this a change was observed."


    def format(self):
        return Warning(type=self.name, description=self.value)
