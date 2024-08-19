import logging
from typing import Any


from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import schema
from pydantic.fields import ModelField
from pymongo.errors import ConnectionFailure, ExecutionTimeout

from app import audit


def field_schema(field: ModelField, **kwargs: Any) -> Any:
    if field.field_info.extra.get("hidden", False):
        raise schema.SkipField(f"{field.name} field is being hidden")
    else:
        return original_field_schema(field, **kwargs)


original_field_schema = schema.field_schema
schema.field_schema = field_schema

app = FastAPI(
    title="MongoDB Audit Service",
    description="""**MongoDB Audit Service - Event-driven architecture demo with Mongo, Changestreams, FastAPI & Azure**""",
    version="1.0.0",
    contact={
        "name": "Event-driven architecture demo with Mongo, Changestreams, FastAPI & Azure",
        "url": "https://github.com/sibie",
    },
)


app.include_router(audit.audit_router)


@app.exception_handler(ConnectionFailure)
async def connection_failure_exception_handler(request, exc):
    logging.exception("DB failed to connect.")

    return JSONResponse(
        status_code=503,
        content="Service is unavailable, please try again later.",
    )


@app.exception_handler(ExecutionTimeout)
async def exceution_timeout_exception_handler(request, exc):
    logging.exception("The request timed out.")
    return JSONResponse(
        status_code=500,
        content="The request taking longer than usual, please try again later.",
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    logging.exception("A validation error occurred in the model.")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def catchall_exception_handler(request, exc):
    logging.exception("Internal server error.")
    return JSONResponse(
        status_code=500,
        content="Internal server error.",
    )


@app.get("/")
async def root():
    return {"message": "Hello! Navigate to /docs to check out the endpoints."}
