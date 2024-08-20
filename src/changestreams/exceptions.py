# Exception to be raised in case change stream was interrupted, used to initiate retry logic.
class StreamInterruptionException(Exception):
    pass


# Exception indicating that failed processing of a task could be resolved by retrying.
class DependencyException(Exception):
    pass
