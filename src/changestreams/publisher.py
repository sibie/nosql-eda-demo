from typing import Optional

from azure.core.messaging import CloudEvent
from azure.eventgrid import EventGridPublisherClient
from azure.identity import DefaultAzureCredential


# A prefix for custom claims to avoid collisions.
_SOURCE_NAMESPACE = "db-"

# Global client used for publishing events to Azure Event Grid.
_eventgrid_client: Optional[EventGridPublisherClient] = None


# Method to retrieve Event Grid client for publishing events.
def get_eventgrid_client(config: dict) -> EventGridPublisherClient:
    global _eventgrid_client

    # Lazy initialization.
    if not _eventgrid_client:
        credential = DefaultAzureCredential()
        _eventgrid_client = EventGridPublisherClient(
            config["EVENT_DOMAIN_ENDPOINT"],
            credential,
        )
        return _eventgrid_client
    return _eventgrid_client


# The naming convention for event type is a combination of source collection name and operation type.
# Eg 1 - (collection = "comments_auditlogs", operation_type = "insert") -> (type = "comments.insert")
# Eg 2 - (collection = "blog_posts_auditlogs", operation_type = "update") -> (type = "blog-posts.update")

def get_type(collection: str, document) -> str:
    prefix = collection.rsplit("_", 1)[0].replace("_", "-") + "."
    return prefix + document["fullDocument"]["operation_type"]


# The naming convention for topic is a combination of namespace, source collection name and "-events" suffix.
# Eg 1 - (collection = "comments_auditlogs") -> (type = "db-comments-events")
# Eg 2 - (collection = "blog_posts_auditlogs") -> (type = "db-blog-posts-events")

def get_source(collection: str) -> str:
    prefix = collection.rsplit("_", 1)[0].replace("_", "-")
    return _SOURCE_NAMESPACE + prefix + "-events"


# Method to publish an event to an Event Grid topic.
def publish_event(config: dict, data: dict, event_type: str, source: str):
    get_eventgrid_client(config).send(
        CloudEvent(
            datacontenttype="application/json",
            data=data,
            type=event_type,
            source=source,
        )
    )
