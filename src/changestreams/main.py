import contextlib
import importlib
import logging
import sys

from pymongo import MongoClient
from pymongo.collection import Collection
from tenacity import (
    RetryError,
    Retrying,
    after_log,
    before_sleep_log,
    wait_random_exponential,
)

from changestream import manage_change_stream
from config import load_config
from exceptions import StreamInterruptedException
from utils import setup_logging, validate_args


# Starts a changestream on a single collection, running a specific job on every observed change event.
# Command syntax --> python main.py <collection> <task> <env>
# Sample command --> python main.py posts auditlogs
# [REQUIRED] collection --> The DB collection to set up a change stream for.
# [REQUIRED] job --> The job to run on each event, matches with corresponding file in /jobs directory.
# [OPTIONAL] env --> Azure App Config label (indicating env) to use when retrieving config data.
# This is useful when we have many environments like UAT, Production, etc. which need separate streams.


def main():
    logger = logging.getLogger(__name__)

    # Get the collection to listen to and the job to run on each change event.
    try:
        collection = sys.argv[1]
        job = sys.argv[2]
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
                    mongo_client: MongoClient = MongoClient(config["DB_CONNECTION_STRING"])
                    logger.info("Successfully connected to the database.")

                except Exception:
                    logger.exception("Failed to connect to database.")
                    raise

                # [STEP 3] Setting up connection to target collection + tokens collection.

                try:
                    stream_target: Collection = mongo_client[config["DB_NAME"]][collection]
                    token_target: Collection = mongo_client[config["DB_NAME"]][config["TOKEN_COLLECTION"]]
                    logger.info("Target and token collections found in the database.")

                except Exception:
                    logger.exception("Failed to find the target and/or token collections in the database.")
                    mongo_client.close()
                    raise

                # [STEP 4] Start and manage the change stream.

                manage_change_stream(
                    config, collection, job, env, stream_target, token_target, cls
                )
                
                logger.exception("The change stream was unexpectedly terminated.")
                raise StreamInterruptedException


if __name__ == "__main__":
    main()
