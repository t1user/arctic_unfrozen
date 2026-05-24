from datetime import datetime as dt
from typing import Any, NamedTuple

import pandas as pd

from arctic.date._mktz import mktz
from arctic.multi_index import groupby_asof

class BitemporalItem(NamedTuple):
    symbol: str
    library: str
    data: pd.DataFrame
    metadata: Any
    last_updated: Any


class BitemporalStore(object):
    """ A versioned pandas DataFrame store.

    As the name hinted, this holds versions of DataFrame by maintaining an extra 'insert time' index internally.
    """

    def __init__(self, version_store: Any, observe_column: str = 'observed_dt') -> None:
        """
        Parameters
        ----------
        version_store : `VersionStore`
            The version store that keeps the underlying data frames
        observe_column : `str`
            Column name for the datetime index that represents the insertion time of a row of data. Unless you intend to
            read raw data out, this column is internal to this store.
        """
        self._store = version_store
        self.observe_column = observe_column

    def read(self, symbol: str, as_of: dt | None = None, raw: bool = False, **kwargs: Any) -> BitemporalItem:
        # TODO: shall we block from_version from getting into super.read?
        """Read data for the named symbol. Returns a BitemporalItem object with
        a data and metdata element (as passed into write).

        Parameters
        ----------
        symbol : `str`
            symbol name for the item
        as_of : `datetime.datetime`
            Return the data as it was as_of the point in time.
        raw : `bool`
            If True, will return the full bitemporal dataframe (i.e. all versions of the data). This also means as_of is
            ignored.

        Returns
        -------
        BitemporalItem namedtuple which contains a .data and .metadata element
        """
        item = self._store.read(symbol, **kwargs)
        last_updated = max(item.data.index.get_level_values(self.observe_column))
        if raw:
            return BitemporalItem(symbol=symbol, library=self._store._arctic_lib.get_name(), data=item.data,
                                  metadata=item.metadata,
                                  last_updated=last_updated)
        else:
            index_names = list(item.data.index.names)
            index_names.remove(self.observe_column)
            return BitemporalItem(symbol=symbol, library=self._store._arctic_lib.get_name(),
                                  data=groupby_asof(item.data, as_of=as_of, dt_col=index_names,
                                                    asof_col=self.observe_column),
                                  metadata=item.metadata, last_updated=last_updated)

    def update(
        self,
        symbol: str,
        data: pd.DataFrame,
        metadata: Any | None = None,
        upsert: bool = True,
        as_of: dt | None = None,
        **kwargs: Any
    ) -> None:
        """ Append 'data' under the specified 'symbol' name to this library.

        Parameters
        ----------
        symbol : `str`
            symbol name for the item
        data : `pd.DataFrame`
            to be persisted
        metadata : `dict`
            An optional dictionary of metadata to persist along with the symbol. If None and there are existing
            metadata, current metadata will be maintained
        upsert : `bool`
            Write 'data' if no previous version exists.
        as_of : `datetime.datetime`
            The "insert time". Default to datetime.now()
        """
        local_tz = mktz()
        if not as_of:
            as_of = dt.now()
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=local_tz)
        data = self._add_observe_dt_index(data, as_of)
        if upsert and not self._store.has_symbol(symbol):
            df = data
        else:
            existing_item = self._store.read(symbol, **kwargs)
            if metadata is None:
                metadata = existing_item.metadata
            df = pd.concat([existing_item.data, data]).sort_index(kind='mergesort')
        self._store.write(symbol, df, metadata=metadata, prune_previous_version=True)

    def write(self, *args: Any, **kwargs: Any) -> None:
        # TODO: may be diff + append?
        raise NotImplementedError('Direct write for BitemporalStore is not supported. Use append instead'
                                  'to add / modify timeseries.')

    def _add_observe_dt_index(self, df: pd.DataFrame, as_of: dt) -> pd.DataFrame:
        index_names = list(df.index.names)
        index_names.append(self.observe_column)
        index = [x + (as_of,) if df.index.nlevels > 1 else (x, as_of) for x in df.index.tolist()]
        df = df.set_index(pd.MultiIndex.from_tuples(index, names=index_names), inplace=False)
        return df
