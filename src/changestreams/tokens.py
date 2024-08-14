from pymongo.collection import Collection
from tenacity import retry, wait_random_exponential


# Method to retrieve the latest resume token from tokens collection to start a change stream.
@retry(wait=wait_random_exponential(multiplier=1, max=10))
def retrieve_token(token_target: Collection, collection: str, job: str):
    query = {"collection": collection, "job": job}
    return result["token"] if (result := token_target.find_one(query)) else None


# Method to update resume token of a change event into corresponding token document.
@retry(wait=wait_random_exponential(multiplier=1, max=10))
def update_token(token_target: Collection, collection: str, job: str, token: dict):
    query = {"collection": collection, "job": job}
    if token_target.find_one(query):
        # Document exists for this collection, updating token.
        update = {"$set": {"token": token}}
        return token_target.update_one(query, update)
    else:
        # Document needs to be created for this collection.
        document = {"collection": collection, "job": job, "token": token}
        return token_target.insert_one(document)
