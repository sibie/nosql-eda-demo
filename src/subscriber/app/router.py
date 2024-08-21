import logging

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_cloudevents import CloudEvent


router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)


# Lets build upon our scenario where we have two collections - comments & blog_posts.
# Changestreams on these collections from API DB will send the events to audit service
# to be documented. Then changestreams on the corresponding audit collections will be
# published on Event Grid under the appropriate topic.

# So here we will introduce two demo webhooks to subscribe to these topics. They will
# be mapped to the topic via destination.properties.endpointUrl property in Event Grid 
# subscriptions defined in infra/components/eventgrid-domain.bicep.


@router.post(
    "/comments",
    summary="Demo webhook to consume comment events.",
    response_description="The changes identified in the comment if any.",
)
async def read_comments(event: CloudEvent):
    # We can use fastapi_cloudevents module for a cloud event schema compatible with pydantic.
    # The change details captured by audit service can be found in the data field.
    data = event.data
    
    logger.info(f"Recieved a change event for comment {data['entity_id']}.")
    logger.info(f"Operation type - {data['operation_type']}")
    logger.info(f"Executed at - {data['executed_at']}")
    logger.info(f"Executed by (User ID) - {data['executed_by']}")

    # For an object-oriented approach, we can also define a schema in this module which would
    # be a copy of the Auditlog model we used in the audit service. Then we can use the
    # parse_obj method to convert the raw data into a pydantic object.

    return JSONResponse(status_code=200, content=jsonable_encoder(data["changes"]))


@router.post(
    "/blog_posts",
    summary="Demo webhook to consume blog post events.",
    response_description="The changes identified in the blog post if any.",
)
async def read_blog_posts(event: CloudEvent):
    data = event.data

    logger.info(f"Recieved a change event for blog post {data['entity_id']}.")
    logger.info(f"Operation type - {data['operation_type']}")
    logger.info(f"Executed at - {data['executed_at']}")
    logger.info(f"Executed by (User ID) - {data['executed_by']}")

    return JSONResponse(status_code=200, content=jsonable_encoder(data["changes"]))
