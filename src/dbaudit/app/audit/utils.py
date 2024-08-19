from datetime import datetime

import pytz
from bson.errors import InvalidId
from bson.objectid import ObjectId
from fastapi import HTTPException


def oid(x):
    try:
        return ObjectId(x)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ObjectId.")


def get_current_datetime():
    current_time = datetime.now(pytz.utc)
    milliseconds = (int(current_time.microsecond / 1000)) * 1000
    current_time = current_time.replace(microsecond=milliseconds)
    return current_time