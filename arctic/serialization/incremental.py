import abc
import hashlib
import logging
from threading import RLock
from collections.abc import Iterator
from typing import Any

import numpy as np
import pandas as pd
from bson import Binary

from arctic._config import ARCTIC_AUTO_EXPAND_CHUNK_SIZE
from arctic.serialization.numpy_records import PandasSerializer
from .._compression import compress
from .._config import MAX_DOCUMENT_SIZE
from .._util import NP_OBJECT_DTYPE
from ..exceptions import ArcticSerializationException

log = logging.getLogger(__name__)


def incremental_checksum(item: bytes, curr_sha: Any | None = None) -> Any:
    curr_sha = hashlib.sha1() if curr_sha is None else curr_sha
    curr_sha.update(item)
    return curr_sha


class LazyIncrementalSerializer(object, metaclass=abc.ABCMeta):
    def __init__(
        self, serializer: Any, input_data: Any, chunk_size: int | float
    ) -> None:
        if chunk_size < 1:
            raise ArcticSerializationException(
                "LazyIncrementalSerializer can't be initialized "
                "with chunk_size < 1 ({})".format(chunk_size)
            )
        if not serializer:
            raise ArcticSerializationException(
                "LazyIncrementalSerializer can't be initialized "
                "with a None serializer object"
            )
        self.input_data = input_data
        self.chunk_size = chunk_size
        self._serializer = serializer
        self._initialized = False
        self._checksum: Binary | None = None

    @abc.abstractmethod
    def __len__(self) -> int:
        pass

    @abc.abstractproperty
    def generator(self) -> Any:
        pass

    @abc.abstractproperty
    def generator_bytes(self) -> Any:
        pass

    @abc.abstractproperty
    def serialize(self) -> Any:
        pass


class IncrementalPandasToRecArraySerializer(LazyIncrementalSerializer):
    def __init__(
        self,
        serializer: Any,
        input_data: pd.DataFrame | pd.Series,
        chunk_size: int | float,
        string_max_len: int | None = None,
    ) -> None:
        super(IncrementalPandasToRecArraySerializer, self).__init__(
            serializer, input_data, chunk_size
        )
        if not isinstance(serializer, PandasSerializer):
            raise ArcticSerializationException(
                "IncrementalPandasToRecArraySerializer requires a serializer of "
                "type PandasSerializer."
            )
        if not isinstance(input_data, (pd.DataFrame, pd.Series)):
            raise ArcticSerializationException(
                "IncrementalPandasToRecArraySerializer requires a pandas DataFrame or "
                "Series as data source input."
            )
        if string_max_len and string_max_len < 1:
            raise ArcticSerializationException(
                "IncrementalPandasToRecArraySerializer can't be initialized "
                "with string_max_len < 1 ({})".format(string_max_len)
            )
        self.string_max_len = string_max_len
        # The state which needs to be lazily initialized
        self._dtype: Any | None = None
        self._shape: tuple[Any, ...] | None = None
        self._rows_per_chunk = 0
        self._total_chunks = 0
        self._has_string_object = False
        self._lock = RLock()

    def _dtype_convert_to_max_len_string(
        self, input_ndtype: Any, fname: Any
    ) -> tuple[Any, bool]:
        if input_ndtype.type not in (np.bytes_, np.str_):
            return input_ndtype, False
        type_sym = "S" if input_ndtype.type == np.bytes_ else "U"
        max_str_len = len(max(self.input_data[fname].astype(type_sym), key=len))
        str_field_dtype = (
            np.dtype("{}{:d}".format(type_sym, max_str_len))
            if max_str_len > 0
            else input_ndtype
        )
        return str_field_dtype, True

    def _get_dtype(self) -> tuple[Any, Any, bool]:
        # Serializer is being called only if can_convert_to_records_without_objects() has passed,
        # which means that the resulting recarray does not contain objects but only numpy types, string, or unicode

        # Serialize the first row to obtain info about row size in bytes (cache first few rows only)
        # Also raise an Exception early, if data are not serializable
        first_chunk, serialized_dtypes = self._serializer.serialize(
            self.input_data[0:10] if len(self) > 0 else self.input_data,
            string_max_len=self.string_max_len,
        )

        # This is the common case, where first row's dtype represents well the whole dataframe's dtype
        if (
            serialized_dtypes is None
            or len(self.input_data) == 0
            or NP_OBJECT_DTYPE not in self.input_data.dtypes.values
        ):
            return first_chunk, serialized_dtypes, False

        # Reaching here means we have at least one column of type object
        # To correctly serialize incrementally, we need to know the final dtype (type and fixed length),
        # using length-conversion information from all values of the object columns

        dtype_arr = []
        has_string_object = False
        for (
            field_name
        ) in (
            serialized_dtypes.names
        ):  # include all column names, along with the expanded multi-index
            field_dtype = serialized_dtypes[field_name]
            if (
                field_name not in self.input_data
                or self.input_data.dtypes[field_name] is NP_OBJECT_DTYPE
            ):
                # Note: .hasobject breaks for timezone-aware datetime64 pandas columns, so compare with dtype('O')
                # if column is an expanded multi index or doesn't contain objects, the serialized 1st row dtype is safe
                field_dtype, with_str_object = self._dtype_convert_to_max_len_string(
                    field_dtype, field_name
                )
                has_string_object |= with_str_object
            dtype_arr.append((field_name, field_dtype))
        return first_chunk, np.dtype(dtype_arr), has_string_object

    def _lazy_init(self) -> None:
        if self._initialized:
            return

        with self._lock:
            if self._initialized:  # intentional double check here
                return
            # Get the dtype of the serialized array (takes into account object types, converted to fixed length strings)
            first_chunk, dtype, has_string_object = self._get_dtype()

            # Compute the number of rows which can fit in a chunk
            rows_per_chunk = 0
            if len(self) > 0 and self.chunk_size > 1:
                rows_per_chunk = (
                    IncrementalPandasToRecArraySerializer._calculate_rows_per_chunk(
                        self.chunk_size, first_chunk
                    )
                )

            # Initialize object's state
            self._dtype = dtype
            shp = list(first_chunk.shape)
            shp[0] = len(self)
            self._shape = tuple(shp)
            self._has_string_object = has_string_object
            self._rows_per_chunk = rows_per_chunk
            self._total_chunks = (
                int(np.ceil(float(len(self)) / self._rows_per_chunk))
                if rows_per_chunk > 0
                else 0
            )
            self._initialized = True

    @staticmethod
    def _calculate_rows_per_chunk(max_chunk_size: int | float, chunk: Any) -> int:
        sze = int(chunk.dtype.itemsize * np.prod(chunk.shape[1:]))
        sze = int(sze if sze < max_chunk_size else max_chunk_size)
        rows_per_chunk = int(max_chunk_size / sze)
        if rows_per_chunk < 1 and ARCTIC_AUTO_EXPAND_CHUNK_SIZE:
            # If a row size is larger than chunk_size, use the maximum document size
            logging.warning(
                "Chunk size of {} is too small to fit a row ({}). "
                "Using maximum document size.".format(max_chunk_size, MAX_DOCUMENT_SIZE)
            )
            # For huge rows, fall-back to using a very large document size, less than max-allowed by MongoDB
            rows_per_chunk = int(MAX_DOCUMENT_SIZE / sze)
        if rows_per_chunk < 1:
            raise ArcticSerializationException(
                "Serialization failed to split data into max sized chunks."
            )
        return rows_per_chunk

    def __len__(self) -> int:
        return len(self.input_data)

    @property
    def shape(self) -> Any:
        self._lazy_init()
        return self._shape

    @property
    def dtype(self) -> Any:
        self._lazy_init()
        return self._dtype

    @property
    def rows_per_chunk(self) -> int:
        self._lazy_init()
        return self._rows_per_chunk

    def checksum(self, from_idx: int | None, to_idx: int | None) -> Binary:
        if self._checksum is None:
            self._lazy_init()
            total_sha: Any = None
            for chunk_bytes, _, _, _ in self.generator_bytes(
                from_idx=from_idx, to_idx=to_idx
            ):
                # TODO: what about compress_array here in batches?
                compressed_chunk = compress(chunk_bytes)
                total_sha = incremental_checksum(compressed_chunk, curr_sha=total_sha)
            assert total_sha is not None
            self._checksum = Binary(total_sha.digest())
        return self._checksum

    def generator(
        self, from_idx: int | None = None, to_idx: int | None = None
    ) -> Iterator[tuple[Any, Any, int, int]]:
        return self._generator(from_idx=from_idx, to_idx=to_idx)

    def generator_bytes(
        self, from_idx: int | None = None, to_idx: int | None = None
    ) -> Iterator[tuple[Any, Any, int, int]]:
        return self._generator(from_idx=from_idx, to_idx=to_idx, get_bytes=True)

    def _generator(
        self, from_idx: int | None, to_idx: int | None, get_bytes: bool = False
    ) -> Iterator[tuple[Any, Any, int, int]]:
        # Note that the range is: [from_idx, to_idx)
        self._lazy_init()

        my_length = len(self)

        # Take into account default arguments and negative indexing (from end offset)
        from_idx = 0 if from_idx is None else from_idx
        if from_idx < 0:
            from_idx = my_length + from_idx
        to_idx = my_length if to_idx is None else min(to_idx, my_length)
        if to_idx < 0:
            to_idx = my_length + to_idx

        # No data, finish iteration
        if my_length == 0 or from_idx >= my_length or from_idx >= to_idx:
            return

        # Perform serialization for each chunk
        while from_idx < to_idx:
            curr_stop = min(from_idx + self._rows_per_chunk, to_idx)

            chunk, _ = self._serializer.serialize(
                self.input_data[from_idx:curr_stop],
                string_max_len=self.string_max_len,
                forced_dtype=self.dtype if self._has_string_object else None,
            )

            # Let the gc collect the intermediate serialized chunk as early as possible
            chunk = chunk.tobytes() if chunk is not None and get_bytes else chunk

            yield chunk, self.dtype, from_idx, curr_stop
            from_idx = curr_stop

    def serialize(self) -> Any:
        return self._serializer.serialize(self.input_data, self.string_max_len)
