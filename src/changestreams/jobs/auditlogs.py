import json
import logging

import httpx
from publisher import publish_event
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from exceptions import DependencyException
from utils import JobInterface, JSONEncoder


# Status codes for which retrying could resolve the issue.
retry_codes = [408, 429, 502, 503, 504]


# Function to post a failed event to a storage container via event grid topic for inspection.
@retry(wait=wait_random_exponential(multiplier=1, max=10))
def backup_failed_event(config: dict, collection: str, payload: dict):
    publish_event(
        config=config,
        data=payload,
        event_type=collection,
        source=config["FAILED_AUDITLOGS_TOPIC"],
    )


# Makes an API call to auditlog service to document change event details.
class Job(JobInterface):
    # Randomly wait up to 2^x * 1 seconds between each retry attempt until the range reaches 60s.
    # Then wait randomly up to 60 seconds afterwards.
    # At 3 attempts, send the payload to a storage queue for inspection as clearly there is an issue.

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(DependencyException),
        wait=wait_random_exponential(multiplier=1, max=10),
    )
    def run(self, config: dict, collection: str, document):
        logger = logging.getLogger(__name__)

        # Structuring the request payload.
        payload = {
            "collection": collection,
            "document": json.loads(JSONEncoder().encode(document["fullDocument"])),
        }

        # Attempting to document the event via auditlogs endpoint.
        try:
            attempts = self.run.retry.statistics["attempt_number"]
            response = httpx.post(config["AUDITLOG_ENDPOINT"], json=payload)
            response.raise_for_status()
            logger.info(f"Auditlog was created successfully after {attempts} attempt(s).")
            return attempts

        except httpx.RequestError as e:
            logger.exception(f"An error occurred while requesting {e.request.url!r}.")
            raise DependencyException from e

        except httpx.HTTPStatusError as e:
            logger.exception(
                f"Error code {e.response.status_code} while requesting {e.request.url!r}.",
                extra={
                    "status_code": e.response.status_code,
                    "reason": e.response.json(),
                    "payload": json.dumps(payload),
                },
            )

            # We only want to retry the task when failure is due to a dependency, eg DB.
            if e.response.status_code not in retry_codes:
                backup_failed_event(config, collection, payload)
                raise

            # For retryable codes, post payload to db-failed-events topic after 3 failed attempts.
            if attempts == 3:
                backup_failed_event(config, collection, payload)

            raise DependencyException from e
