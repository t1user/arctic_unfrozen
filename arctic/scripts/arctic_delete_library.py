import logging
import optparse
from typing import Any

from .utils import get_db_connection, setup_logging
from ..arctic import Arctic

logger = logging.getLogger(__name__)


def main() -> None:
    usage = """usage: %prog [options]

    Deletes the named library from a user's database.

    Example:
        %prog --host=hostname --library=arctic_jblackburn.my_library
    """
    setup_logging()

    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "--host",
        default="localhost",
        help="Hostname, or clustername. Default: localhost",
    )
    parser.add_option(
        "--library", help="The name of the library. e.g. 'arctic_jblackburn.lib'"
    )

    opts, _ = parser.parse_args()

    if not opts.library:
        parser.error(
            "Must specify the full path of the library e.g. arctic_jblackburn.lib!"
        )

    print("Deleting: %s on mongo %s" % (opts.library, opts.host))
    db_name = opts.library[: opts.library.index(".")] if "." in opts.library else None
    c: Any = get_db_connection(opts.host, db_name)
    store = Arctic(c)
    store.delete_library(opts.library)

    logger.info("Library %s deleted" % opts.library)


if __name__ == "__main__":
    main()
