import logging
from collections import namedtuple
from typing import Any

from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


def authenticate(db: Any, user: str, password: str) -> bool:
    """
    Return True / False on authentication success.

    PyMongo 2.6 changed the auth API to raise on Auth failure.
    """
    try:
        logger.debug("Authenticating {} with {}".format(db, user))
        return db.authenticate(user, password)
    except OperationFailure as e:
        logger.debug("Auth Error %s" % e)
    return False


MongoCredentials = namedtuple("MongoCredentials", ['database', 'user', 'password'])
Credential = MongoCredentials


def get_auth(host: str, app_name: str, database_name: str) -> Any:
    """
    Authentication hook to allow plugging in custom authentication credential providers
    """
    from .hooks import _get_auth_hook
    return _get_auth_hook(host, app_name, database_name)
