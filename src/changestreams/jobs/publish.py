import json
import logging

from publisher import get_type, get_source, publish_event
from tenacity import retry, wait_random_exponential
from utils import JobInterface, JSONEncoder


# Publishes auditlogs to corresponding event grid topic, where it can be used by subscribers.
class Job(JobInterface):
    @retry(wait=wait_random_exponential(multiplier=1, max=10))
    def run(self, config: dict, collection: str, document):
        logger = logging.getLogger(__name__)

        try:
            data = json.loads(JSONEncoder().encode(document["fullDocument"]))

            publish_event(
                config=config,
                data=data,
                event_type=get_type(collection, document),
                source=get_source(collection),
            )
            attempts = self.run.retry.statistics["attempt_number"]
            logger.info(f"Change event was published successfully after {attempts} attempts.")
            return attempts

        except Exception as e:
            logger.exception(
                f"Error while publishing the {collection} event.",
                exc_info=True,
                extra={
                    "reason": e,
                    "data": data,
                },
            )
            raise
