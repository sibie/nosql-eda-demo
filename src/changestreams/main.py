import contextlib
import importlib
import logging
import sys

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from tenacity import (
    RetryError,
    Retrying,
    after_log,
    before_sleep_log,
    wait_random_exponential,
)

from changestream import manage_change_stream
from config import get_connection_str_by_job, get_db_name_by_job, load_config
from exceptions import StreamInterruptionException
from utils import setup_logging, validate_args


# Starts a changestream on a single collection, running a specific job on every observed change event.
# Command syntax --> python main.py <job> <collection> <env>
# Sample command --> python main.py audit posts
# [REQUIRED] collection --> The DB collection to set up a change stream for.
# [REQUIRED] job --> The job to run on each event, matches with corresponding file in /jobs directory.
# [OPTIONAL] env --> Azure App Config label (indicating env) to use when retrieving config data.
# This is useful when we have many environments like UAT, Production, etc. which need separate streams.


def main():
    logger = logging.getLogger(__name__)

    # Get the collection to listen to and the job to run on each change event.
    try:
        job = sys.argv[1]
        collection = sys.argv[2]
        env = sys.argv[3] if len(sys.argv) == 4 else "\0"  # \0 -> (No Label)

    except IndexError:
        logger.exception("Required arguments were not provided.") 
        sys.exit()
    
    if not validate_args(collection, job):
        logger.warning("Failed to proceed as argument combination is invalid.")
        sys.exit()

    # Adding custom record factory to logger so custom attributes are passed with every message.
    setup_logging(collection, job, env)

    logger.info(f"Setting up dependencies to build a change stream on '{collection} collection'...")

    # Identifying the job to be executed on change stream events.
    try:
        cls = getattr(importlib.import_module(f"jobs.{job}"), "Job")
        logger.info(f"Job '{job}' found to execute for change events.")

    except Exception:
        logger.exception(f"Failed to find '{job}' in the changestreams/jobs directory.")
        sys.exit()

    with contextlib.suppress(RetryError):
        for attempt in Retrying(
            before_sleep=before_sleep_log(logger, logging.INFO),
            after=after_log(logger, logging.INFO),
            wait=wait_random_exponential(multiplier=1, max=60),
        ):
            with attempt:

                # [STEP 1] Load config from Azure App Configuration. Use .env if $RUN_ENV=LOCAL.

                try:
                    config = load_config(env)
                    logger.info("Successfully loaded configuration details.")

                except Exception:
                    logger.exception("Failed to retrieve configuration details.")
                    raise

                # [STEP 2] Setting up connection to the DB.

                try:
                    # We have assumed that main API DB is separate from audit DB.
                    # So we need to identify which to connect to based on the job.
                    connection_str = get_connection_str_by_job(config, job)
                    db_name = get_db_name_by_job(config, job)

                    db_client: MongoClient = MongoClient(connection_str)
                    db: Database = db_client[db_name]
                    logger.info("Successfully connected to the database.")

                    # Typically the collection will be auto-created if it doesn't exist.
                    # To avoid this, we check if it exists before proceeding.
                    if collection not in db.list_collection_names():
                        logger.warning(f"Collection {collection} not found in DB {db_name}")
                        db_client.close()
                        sys.exit()

                except Exception:
                    logger.exception("Failed to connect to database.")
                    raise

                # [STEP 3] Setting up connection to target collection + tokens collection.

                try:
                    stream_target: Collection = db[collection]
                    token_target: Collection = db[config["TOKEN_COLLECTION"]]
                    logger.info("Target and token collections found in the database.")

                except Exception:
                    logger.exception("Failed to find the target and/or token collections in the database.")
                    db_client.close()
                    raise

                # [STEP 4] Start and manage the change stream.

                manage_change_stream(
                    config=config,
                    collection=collection,
                    job=job,
                    stream_target=stream_target,
                    token_target=token_target,
                    cls=cls,
                )
                
                # In case the retry mechanism within manage_change_stream fails, then we
                # raise a custom exception here in main to reset the stream from scratch.
                logger.exception("The change stream was unexpectedly terminated.")
                db_client.close()
                raise StreamInterruptionException


if __name__ == "__main__":
    main()
