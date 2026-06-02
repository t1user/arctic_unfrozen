import logging
from typing import Any

from ..auth import create_client, get_auth

logger = logging.getLogger(__name__)


def get_db_connection(host: str, db_name: str | None) -> Any:
    """
    Create a Mongo client using admin credentials when available, otherwise
    credentials for the requested database.

    Tries:
      - Auth'ing against admin as 'admin' ; credentials: <host>/arctic/admin/admin
      - Auth'ing against db_name (which may be None if auth'ing against admin above)

    The connection attempt remains lazy until the first database operation.
    """
    admin_creds = get_auth(host, "admin", "admin")
    user_creds = get_auth(host, "arctic", db_name)

    return create_client(host, admin_creds or user_creds)


def setup_logging() -> None:
    """Logging setup for console scripts"""
    logging.basicConfig(format="%(asctime)s %(message)s", level="INFO")
