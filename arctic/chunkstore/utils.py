"""
Helper functions that are not 'core' to chunkstore
"""
from collections.abc import Callable, Iterator
from typing import Any


def read_apply(lib: Any, symbol: str, func: Callable[[Any], Any], chunk_range: Any = None) -> Iterator[Any]:
    """
    Apply `func` to each chunk in lib.symbol

    Parameters
    ----------
    lib: arctic library
    symbol: str
        the symbol for the given item in the DB
    chunk_range: None, or a range object
        allows you to subset the chunks by range

    Returns
    -------
    generator
    """
    for chunk in lib.iterator(symbol, chunk_range=chunk_range):
        yield func(chunk)
