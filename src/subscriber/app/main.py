from fastapi import FastAPI

from app.router import router


# NOTE This is just a theoretical example. The actual API service and DB are out of the scope of this demo.
# The aim is to show how we can audit Mongo data via changestreams and tie this with Azure to demonstrate
# an example of event-driven architecture.

app = FastAPI(
    title="Demo Subscriber Service",
    description="""**Simple service to showcase how change events can be consumed by subscribers.**""",
    version="1.0.0",
    contact={
        "name": "Event-driven architecture demo with Mongo, Changestreams, FastAPI & Azure",
        "url": "https://github.com/sibie",
    },
)


app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Hello! Navigate to /docs to check out the endpoints."}
