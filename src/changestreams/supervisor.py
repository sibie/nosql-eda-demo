import os

from pymongo import MongoClient

from config import load_config

# This script can be used to dynamically generate supervisord.conf file with:
# -> Changestream listeners on all API collections to post to Auditlogs service.
# -> Changestream listeners on all auditlog collections to post to Event Grid topic.

# Sample program block for an source collection listener.
api_collection_program_block = [
    "[program:<REPLACE>_to_auditlogs] ; Listen to '<REPLACE>' collection and create auditlogs for observed changes.",
    "directory=%(ENV_CHANGESTREAM_DIR)s",
    "priority=999",
    "autostart=true",
    "startsecs=1",
    "startretries=3",
    "autorestart=true",
    "command=python3 -u changestream.py <REPLACE> auditlogs",
    "stderr_logfile=%(ENV_CHANGESTREAM_DIR)s/logs/<REPLACE>_to_auditlogs.log",
    "stderr_logfile_maxbytes=25MB",
    "stderr_logfile_backups=0",
]

# Sample program block for an auditlog collection listener.
auditlog_collection_program_block = [
    "[program:<REPLACE>_to_event_grid] ; Listen to '<REPLACE>' collection and post to Event Grid topic'",
    "directory=%(ENV_CHANGESTREAM_DIR)s",
    "priority=999",
    "autostart=true",
    "startsecs=1",
    "startretries=3",
    "autorestart=true",
    "command=python3 -u changestream.py <REPLACE> event_publisher",
    "stderr_logfile=%(ENV_CHANGESTREAM_DIR)s/logs/<REPLACE>_to_event_grid.log",
    "stderr_logfile_maxbytes=25MB",
    "stderr_logfile_backups=0",
]


# Function to pick up list of collections in the DB.
def get_collection_list():
    # Ensure $RUN_ENV=LOCAL is set so config is taken from environment.
    config = load_config()
    print("Configuration loaded.")

    # Connecting to the DB and retrieving collection list.
    mongo_client = MongoClient(config["DB_CONNECTION_STRING"])
    db = mongo_client[config["DB_NAME"]]
    collections = db.list_collection_names()
    print("Collection list retrieved.")

    # Close the connection and return the collection list.
    mongo_client.close()
    return sorted([collection for collection in collections])


# Function to generate a conf program block for a collection.
def generate_program_block(collection: str):
    block: list = []
    if "auditlogs" in collection:
        block.extend(
            line.replace("<REPLACE>", collection)
            for line in auditlog_collection_program_block
        )
    else:
        block.extend(
            line.replace("<REPLACE>", collection)
            for line in api_collection_program_block
        )
    return block


# Function to generate the supervisor conf file in changestreams dir.
def generate_conf():
    # Getting collection list.
    collections = get_collection_list()

    # Deleting old conf file if present.
    if os.path.exists("supervisord.conf"):
        os.remove("supervisord.conf")
        print("Deleted the old supervisord.conf file.")

    # Getting the base supervisord configuration from example file.
    with open("supervisord.example", "r") as file:
        base_config = file.read()
        print("Retrieved base .conf file reference for supervisor.")

    with open("supervisord.conf", "a") as file:
        # Adding the base supervisord configuration.
        file.write(base_config)
        print("Added base configuration for supervisor.")

        # Generating program block for each collection and adding to conf.
        for collection in collections:
            program_block = generate_program_block(collection)
            for line in program_block:
                file.write(line)
                file.write("\n")
            file.write("\n")
            print(f"Added program block for {collection} collection.")


if __name__ == "__main__":
    generate_conf()
