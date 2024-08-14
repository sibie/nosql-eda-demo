import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from bson import ObjectId


# Interface to be implemented by different job classes.
class JobInterface(ABC):
    @abstractmethod
    def run(self, config: dict, collection: str, document):
        pass


# Custom handling of ObjectID and Datetime type values for JSON Encoder.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


# Function to configure Python logging for the module.
def setup_logging(collection: str, job: str, env: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d |:| %(levelname)s |:| %(name)s |:| %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Adding custom attributes to the Log Record factory to be included in every message.
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.collection = collection
        record.job = job
        
        # Optional env attribute if used in Azure App Config.
        if env != "/0":
            record.env = env
        
        return record

    logging.setLogRecordFactory(record_factory)


# Method to validate args provided at run time.
def validate_args(collection: str, job: str) -> bool:
    # Data audit job can only be run on change events from source collection.
    if job == "auditlogs":
        if "auditlogs" in collection:
            return False
    
    # Event publication job can only be run on change events from auditlog collection.
    if job == "events":
        if "auditlogs" not in collection:
            return False 
    
    return True
