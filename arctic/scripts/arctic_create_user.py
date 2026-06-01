import argparse
import base64
import logging
import uuid
from typing import Any

from arctic.arctic import Arctic
from ..auth import create_client, get_auth

logger = logging.getLogger(__name__)


def main() -> None:
    usage = """arctic_create_user --host research [--db mongoose_user] [--write] user

    Creates the user's personal Arctic mongo database
    Or add a user to an existing Mongo Database.
    """

    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument("--host", default='localhost', help="Hostname, or clustername. Default: localhost")
    parser.add_argument("--db", default=None, help="Database to add user on. Default: mongoose_<user>")
    parser.add_argument("--password", default=None, help="Password. Default: random")
    parser.add_argument("--write", action='store_true', default=False, help="Used for granting write access to someone else's DB")
    parser.add_argument("users", nargs='+', help="Users to add.")

    args = parser.parse_args()

    credentials = get_auth(args.host, "admin", "admin")
    c: Any = create_client(args.host, credentials)

    for user in args.users:
        write_access = args.write
        p = args.password
        if p is None:
            p = base64.b64encode(uuid.uuid4().bytes).replace(b'/', b'')[:12].decode("ascii")
        db = args.db
        if not db:
            # Users always have write access to their database
            write_access = True
            db = Arctic.DB_PREFIX + '_' + user

        # Add the user to the database
        role = "readWrite" if write_access else "read"
        c[db].command("createUser", user, pwd=p, roles=[{"role": role, "db": db}])

        logger.info("Granted: {user} [{permission}] to {db}".format(user=user,
                                                                    permission='WRITE' if write_access else 'READ',
                                                                    db=db))
        logger.info("User creds: {db}/{user}/{password}".format(user=user,
                                                                db=db,
                                                                password=p,
                                                                ))


if __name__ == '__main__':
    main()
