class KBCoreError(Exception):
    """Base class for domain exceptions."""


class ParserNotFoundError(KBCoreError):
    pass


class CollectionNotFoundError(KBCoreError):
    pass


class DocumentNotFoundError(KBCoreError):
    pass
