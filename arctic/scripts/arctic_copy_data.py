import argparse
import logging
import os
import pwd
from collections.abc import Callable, Sequence
from multiprocessing import Pool
from typing import Any, cast

import pandas as pd

from arctic.decorators import _get_host
from arctic.store.audit import ArcticTransaction
from .utils import setup_logging
from ..date import DateRange, to_pandas_closed_closed, CLOSED_OPEN, OPEN_CLOSED
from ..hosts import get_arctic_lib

logger = logging.getLogger(__name__)

# Use the UID rather than environment variables for auditing
USER = pwd.getpwuid(os.getuid())[0]


def copy_symbols_helper(src: Any, dest: Any, log: str, force: bool, splice: bool) -> Callable[[Sequence[str]], None]:
    def _copy_symbol(symbols: Sequence[str]) -> None:
        for symbol in symbols:
            with ArcticTransaction(dest, symbol, USER, log) as mt:
                existing_data = dest.has_symbol(symbol)
                if existing_data:
                    if force:
                        logger.warn("Symbol: %s already exists in destination, OVERWRITING" % symbol)
                    elif splice:
                        logger.warn("Symbol: %s already exists in destination, splicing in new data" % symbol)
                    else:
                        logger.warn("Symbol: {} already exists in {}@{}, use --force to overwrite or --splice to join "
                                    "with existing data".format(symbol, _get_host(dest).get('l'),
                                                                _get_host(dest).get('mhost')))
                        continue

                version = src.read(symbol)
                new_data = version.data

                if existing_data and splice:
                    original_data = dest.read(symbol).data
                    preserve_start_range = cast(
                        DateRange,
                        to_pandas_closed_closed(DateRange(None, new_data.index[0].to_pydatetime(),
                                                          interval=CLOSED_OPEN)),
                    )
                    preserve_end_range = cast(
                        DateRange,
                        to_pandas_closed_closed(DateRange(new_data.index[-1].to_pydatetime(),
                                                          None,
                                                          interval=OPEN_CLOSED)),
                    )
                    preserve_start = preserve_start_range.end
                    preserve_end = preserve_end_range.start
                    if not original_data.index.tz:
                        # No timezone on the original, should we even allow this?
                        preserve_start = preserve_start.replace(tzinfo=None)
                        preserve_end = preserve_end.replace(tzinfo=None)
                    before = original_data.loc[:preserve_start]
                    after = original_data[preserve_end:]
                    new_data = pd.concat([before, new_data, after])

                mt.write(symbol, new_data, metadata=version.metadata)
    return _copy_symbol


def main() -> None:
    usage = """
    Copy data from one MongoDB instance to another.

    Example:
        arctic_copy_data --log "Copying data" --src user.library@host1 --dest user.library@host2 symbol1 symbol2
    """
    setup_logging()
    p = argparse.ArgumentParser(usage=usage)
    p.add_argument("--src", required=True, help="Source MongoDB like: library@hostname:port")
    p.add_argument("--dest", required=True, help="Destination MongoDB like: library@hostname:port")
    p.add_argument("--log", required=True, help="Data CR")
    p.add_argument("--force", default=False, action='store_true', help="Force overwrite of existing data for symbol.")
    p.add_argument("--splice", default=False, action='store_true', help="Keep existing data before and after the new data.")
    p.add_argument("--parallel", default=1, type=int, help="Number of imports to run in parallel.")
    p.add_argument("symbols", nargs='+', type=str, help="List of symbol regexes to copy from source to dest.")

    opts = p.parse_args()

    src = get_arctic_lib(opts.src)
    dest = get_arctic_lib(opts.dest)

    logger.info("Copying data from %s -> %s" % (opts.src, opts.dest))

    # Prune the list of symbols from the library according to the list of symbols.
    required_symbols_set: set[str] = set()
    for symbol in opts.symbols:
        required_symbols_set.update(src.list_symbols(regex=symbol))
    required_symbols = sorted(required_symbols_set)

    logger.info("Copying: {} symbols".format(len(required_symbols)))
    if len(required_symbols) < 1:
        logger.warn("No symbols found that matched those provided.")
        return

    # Function we'll call to do the data copying
    copy_symbol = copy_symbols_helper(src, dest, opts.log, opts.force, opts.splice)

    if opts.parallel > 1:
        logger.info("Starting: {} jobs".format(opts.parallel))
        pool = Pool(processes=opts.parallel)
        # Break the jobs into chunks for multiprocessing
        chunk_size = len(required_symbols) // opts.parallel
        chunk_size = max(chunk_size, 1)
        chunks = [required_symbols[offs:offs + chunk_size] for offs in
                  range(0, len(required_symbols), chunk_size)]
        assert sum(len(x) for x in chunks) == len(required_symbols)
        pool.apply(copy_symbol, chunks)
    else:
        copy_symbol(required_symbols)


if __name__ == '__main__':
    main()
