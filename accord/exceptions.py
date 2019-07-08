class RestoreSignal(Exception):
    pass


class NoPostgresBackup(Exception):
    pass


class MissingSyncNode(Exception):
    pass


class InvalidReplicaCount(Exception):
    pass


class UnableToSync(Exception):
    pass
