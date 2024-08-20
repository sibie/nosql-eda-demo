import os

from pymongo import MongoClient

from config import load_config

# This script can be used to dynamically generate supervisord.conf file with:
# -> Changestream listeners on all API collections to post to Auditlogs service.
# -> Changestream listeners on all auditlog collections to post to Event Grid topic.

# Sample program block for an API collection listener.
api_collection_program_block = [
    "[program:audit_<REPLACE>] ; Listen to '<REPLACE>' collection and audit observed change events.",
    "directory=%(ENV_CHANGESTREAM_DIR)s",
    "priority=999",
    "autostart=true",
    "startsecs=1",
    "startretries=3",
    "autorestart=true",
    "command=python3 -u main.py audit <REPLACE>",
    "stderr_logfile=%(ENV_CHANGESTREAM_DIR)s/logs/audit_<REPLACE>.log",
    "stderr_logfile_maxbytes=25MB",
    "stderr_logfile_backups=0",
]

# Sample program block for an audit collection listener.
auditlog_collection_program_block = [
    "[program:publish_<REPLACE>] ; Listen to '<REPLACE>' collection and publish to Event Grid topic'",
    "directory=%(ENV_CHANGESTREAM_DIR)s",
    "priority=999",
    "autostart=true",
    "startsecs=1",
    "startretries=3",
    "autorestart=true",
    "command=python3 -u main.py publish <REPLACE>",
    "stderr_logfile=%(ENV_CHANGESTREAM_DIR)s/logs/publish_<REPLACE>.log",
    "stderr_logfile_maxbytes=25MB",
    "stderr_logfile_backups=0",
]


# Function to pick up list of collections in the DB.
def get_collection_list(config: dict, connection_str: str, db_name: str):
    # Connecting to the DB and retrieving collection list.
    mongo_client = MongoClient(config[connection_str])
    db = mongo_client[config[db_name]]
    collections = db.list_collection_names()

    # Remove tokens collection if present, it is specific to changestreams.
    if config["TOKEN_COLLECTION"] in collections:
        collections.remove(config["TOKEN_COLLECTION"])

    # Close the connection and return the collection list.
    mongo_client.close()
    return sorted([collection for collection in collections])


# Function to generate a conf program block for a collection.
def generate_program_block(collection: str, source: str):
    block: list = []
    if source == "audit":
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
    # Ensure $RUN_ENV=LOCAL is set so config is taken from environment.
    config = load_config()
    print("Configuration loaded.")

    # Getting collection list.
    api_collections = get_collection_list(
        config=config,
        connection_str=config["API_DB_CONNECTION_STRING"],
        db_name=config["API_DB_NAME"],
    )
    print("API collection list retrieved.")

    audit_collections = get_collection_list(
        config=config,
        connection_str=config["AUDIT_DB_CONNECTION_STRING"],
        db_name=config["AUDIT_DB_NAME"],
    )
    print("Audit collection list retrieved.")

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
        for collection in api_collections:
            program_block = generate_program_block(collection, "api")
            for line in program_block:
                file.write(line)
                file.write("\n")
            file.write("\n")
            print(f"Added program block for {collection} API collection.")
        
        for collection in audit_collections:
            program_block = generate_program_block(collection, "audit")
            for line in program_block:
                file.write(line)
                file.write("\n")
            file.write("\n")
            print(f"Added program block for {collection} audit collection.")


if __name__ == "__main__":
    generate_conf()
