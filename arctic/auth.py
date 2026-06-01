import logging
from typing import Any, NamedTuple

from pymongo import MongoClient

logger = logging.getLogger(__name__)


class MongoCredentials(NamedTuple):
    database: str
    user: str
    password: str


Credential = MongoCredentials


def get_auth(host: str, app_name: str, database_name: str | None) -> MongoCredentials | None:
    """
    Authentication hook to allow plugging in custom authentication credential providers
    """
    from .hooks import _get_auth_hook
    return _get_auth_hook(host, app_name, database_name)


def create_client(host: str, credentials: MongoCredentials | None = None, **kwargs: Any) -> MongoClient[dict[str, Any]]:
    """Create a Mongo client with optional credentials resolved before connecting."""
    from .hooks import get_mongodb_uri

    if credentials is not None:
        kwargs.update(username=credentials.user, password=credentials.password, authSource=credentials.database)
    return MongoClient(get_mongodb_uri(host), **kwargs)
