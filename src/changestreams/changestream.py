import logging
import time

from pymongo.collection import Collection
from pymongo.change_stream import CollectionChangeStream
from tenacity import (
    before_sleep_log,
    retry,
    wait_random_exponential,
)

from tokens import retrieve_token, update_token


# Method to manage the stream and keep it alive, restart with latest resume token in case of failures.
@retry(
    wait=wait_random_exponential(multiplier=1, max=60),
    before_sleep=before_sleep_log(logging.getLogger(__name__), logging.ERROR, exc_info=True)
)
def manage_change_stream(
    config: dict,
    collection: str,
    job: str,
    stream_target: Collection,
    token_target: Collection,
    cls,
):
    logger = logging.getLogger(__name__)

    # Starting point of the stream is queried from DB.
    latest_token = retrieve_token(token_target, collection, job)

    logger.info(f"Starting change stream...")
    cursor: CollectionChangeStream = stream_target.watch(
        pipeline=[
            {"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}},
            {"$project": {"_id": 1, "fullDocument": 1, "ns": 1, "documentKey": 1}},
        ],
        full_document="updateLookup",
        resume_after=latest_token,
    )
    cursor.try_next

    logger.info("Listening for change events...")
    for document in cursor:
        logger.info("Event observed.")
        start = time.time()

        # Resource ID would be under a different key for standard docs and auditlogs.
        # Keeping it simple as this is a demo, but a more effective solution would
        # be needed if we introduced more job types with different collection scopes.
        if job == "publish":
            resource_id = document["fullDocument"]["resource_id"]
        else:
            resource_id = document["fullDocument"]["_id"]

        # Run the required job for the change event.
        try:
            cls().run(config, collection, document)

        except Exception:
            logger.exception(f"Failed to complete {job} job for resource {resource_id}.")

            # Updating latest token into mongo before proceeding.
            update_token(token_target, collection, job, cursor.resume_token)
            logger.info("Resume token updated.")
            continue

        elapsed_time = time.time() - start
        logger.info(f"Completed {job} job for resource {resource_id} in {round(elapsed_time, 4)} seconds.")

        # Updating latest token into mongo before proceeding.
        update_token(token_target, collection, job, cursor.resume_token)
        logger.info("Resume token updated.")
    
    # Ideally the stream should run indefinitely. If unexpectedly terminated, the stream will be restarted from main.
    cursor.close()
    return
