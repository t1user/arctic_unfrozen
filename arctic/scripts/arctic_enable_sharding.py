import optparse
from typing import Any

from .utils import setup_logging
from .._util import enable_sharding
from ..arctic import Arctic
from ..auth import create_client, get_auth


def main() -> None:
    usage = """usage: %prog [options] arg1=value, arg2=value

    Enables sharding on the specified arctic library.
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

    if not opts.library or "." not in opts.library:
        parser.error(
            "must specify the full path of the library e.g. arctic_jblackburn.lib!"
        )

    print("Enabling-sharding: %s on mongo %s" % (opts.library, opts.host))

    credentials = get_auth(opts.host, "admin", "admin")
    c: Any = create_client(opts.host, credentials)
    store = Arctic(c)
    enable_sharding(store, opts.library)


if __name__ == "__main__":
    main()
