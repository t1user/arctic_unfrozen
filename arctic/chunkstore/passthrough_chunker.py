from collections.abc import Iterator
from typing import Any

from pandas import DataFrame, Series

from ._chunker import Chunker


class PassthroughChunker(Chunker):
    TYPE = "passthru"

    def to_chunks(
        self, data: Any, **kwargs: Any
    ) -> Iterator[tuple[bytes, bytes, bytes, Any]]:
        """
        pass thru chunker of the dataframe/series

        returns
        -------
        ('NA', 'NA', 'NA', dataframe/series)
        """
        if len(data) > 0:
            yield b"NA", b"NA", b"NA", data

    def to_range(self, start: Any, end: Any) -> bytes:
        """
        returns a RangeObject from start/end sentinels.

        returns
        -------
        string
        """
        return b"NA"

    def chunk_to_str(self, chunk_id: Any) -> bytes:
        """
        Converts parts of a chunk range (start or end) to a string

        returns
        -------
        string
        """
        return b"NA"

    def to_mongo(self, range_obj: Any) -> dict[str, Any]:
        """
        returns mongo query against range object.
        since range object is not valid, returns empty dict

        returns
        -------
        string
        """
        return {}

    def filter(self, data: DataFrame | Series, range_obj: Any) -> DataFrame | Series:
        """
        ensures data is properly subset to the range in range_obj.
        since range object is not valid, returns data

        returns
        -------
        data
        """
        return data

    def exclude(self, data: DataFrame | Series, range_obj: Any) -> DataFrame | Series:
        """
        Removes data within the bounds of the range object.
        Since range object is not valid for this chunk type,
        returns nothing

        returns
        -------
        empty dataframe or series
        """
        if isinstance(data, DataFrame):
            return DataFrame()
        else:
            return Series()
