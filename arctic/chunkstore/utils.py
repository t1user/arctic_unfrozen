"""
Helper functions that are not 'core' to chunkstore
"""
from collections.abc import Callable, Iterator
from typing import Any, Protocol, TypeVar


Chunk = TypeVar("Chunk", covariant=True)
Result = TypeVar("Result")


class _ChunkIteratorLibrary(Protocol[Chunk]):
    def iterator(self, symbol: str, chunk_range: Any = None) -> Iterator[Chunk]:
        ...


def read_apply(
    lib: _ChunkIteratorLibrary[Chunk], symbol: str, func: Callable[[Chunk], Result], chunk_range: Any = None
) -> Iterator[Result]:
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
