'''
Utility functions for multi-index dataframes. Useful for creating bi-temporal timeseries.
'''
import logging
from datetime import datetime
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from pandas import to_datetime as dt

from .date import mktz

PD_VER = pd.__version__
logger = logging.getLogger(__name__)


# ----------------------- Grouping and Aggregating  ---------------------------- #

def _lexsort_depth(index: Any) -> int:
    """Return MultiIndex lexsort depth across pandas versions."""
    return getattr(index, "lexsort_depth", index._lexsort_depth)


def fancy_group_by(
    df: pd.DataFrame,
    grouping_level: int | str | list[str] = 0,
    aggregate_level: int | str = 1,
    method: str = 'last',
    max_: Any | None = None,
    min_: Any | None = None,
    within: Any | None = None,
) -> pd.DataFrame:
    """ Dataframe group-by operation that supports aggregating by different methods on the index.

    Parameters
    ----------
    df: ``DataFrame``
        Pandas dataframe with a MultiIndex
    grouping_level: ``int`` or ``str`` or ``list`` of ``str``
        Index level to group by. Defaults to 0.
    aggregate_level: ``int`` or ``str``
        Index level to aggregate by. Defaults to 1.
    method: ``str``
        Aggregation method. One of
            last: Use the last (lexicographically) value from each group
            first: Use the first value from each group
    max_: <any>
        If set, will limit results to those having aggregate level values <= this value
    min_: <any>
        If set, will limit results to those having aggregate level values >= this value
    within: Any type supported by the index, or ``DateOffset``/timedelta-like for ``DatetimeIndex``.
        If set, will limit results to those having aggregate level values within this range of the group value.
        Note that this is currently unsupported for Multi-index of depth > 2
    """
    if method not in ('first', 'last'):
        raise ValueError('Invalid method')

    if isinstance(aggregate_level, str):
        aggregate_level_index = df.index.names.index(aggregate_level)
    else:
        aggregate_level_index = aggregate_level

    # Trim any rows outside the aggregate value bounds
    if max_ is not None or min_ is not None or within is not None:
        agg_idx = df.index.get_level_values(aggregate_level_index)
        mask = np.full(len(agg_idx), True, dtype='b1')
        if max_ is not None:
            mask &= (agg_idx <= max_)
        if min_ is not None:
            mask &= (agg_idx >= min_)
        if within is not None:
            group_idx = df.index.get_level_values(grouping_level)
            if isinstance(agg_idx, pd.DatetimeIndex):
                mask &= (group_idx >= agg_idx.shift(-1, freq=within))
            else:
                mask &= (group_idx >= (agg_idx - within))
        df = df.loc[mask]

    # The sort order must be correct in order of grouping_level -> aggregate_level for the aggregation methods
    # to work properly. We can check the sortdepth to see if this is in fact the case and resort if necessary.
    # TODO: this might need tweaking if the levels are around the wrong way
    if _lexsort_depth(df.index) < (aggregate_level_index + 1):
        df = df.sort_index(level=grouping_level)

    gb = df.groupby(level=grouping_level)
    if method == 'last':
        return gb.last()
    return gb.first()


# --------- Common as-of-date use case -------------- #

def groupby_asof(
    df: pd.DataFrame,
    as_of: datetime | None = None,
    dt_col: str | int = 'sample_dt',
    asof_col: str | int = 'observed_dt',
) -> pd.DataFrame:
    ''' Common use case for selecting the latest rows from a bitemporal dataframe as-of a certain date.

    Parameters
    ----------
    df: ``pd.DataFrame``
        Dataframe with a MultiIndex index
    as_of: ``datetime``
        Return a timeseries with values observed <= this as-of date. By default, the latest observed
        values will be returned.
    dt_col: ``str`` or ``int``
        Name or index of the column in the MultiIndex that is the sample date
    asof_col: ``str`` or ``int``
        Name or index of the column in the MultiIndex that is the observed date
    '''
    if as_of:
        if as_of.tzinfo is None and df.index.get_level_values(asof_col).tz is not None:
            as_of = as_of.replace(tzinfo=mktz())
    return fancy_group_by(df,
                          grouping_level=dt_col,
                          aggregate_level=asof_col,
                          method='last',
                          max_=as_of)


# ----------------------- Insert/Append ---------------------------- #


def multi_index_insert_row(df: pd.DataFrame, index_row: Sequence[Any], values_row: Any) -> pd.DataFrame:
    """ Return a new dataframe with a row inserted for a multi-index dataframe.
        This will sort the rows according to the ordered multi-index levels.
    """
    if PD_VER < '0.24.0':
        row_index = pd.MultiIndex(levels=[[i] for i in index_row],
                                  labels=[[0] for i in index_row],
                                  names=df.index.names)
    else:
        row_index = pd.MultiIndex(levels=[[i] for i in index_row],
                                  codes=[[0] for i in index_row],
                                  names=df.index.names)
    row = pd.DataFrame(values_row, index=row_index, columns=df.columns)
    df = pd.concat((df, row))
    if _lexsort_depth(df.index) == len(index_row) and df.index[-2] < df.index[-1]:
        # We've just appended a row to an already-sorted dataframe
        return df
    # The df wasn't sorted or the row has to be put in the middle somewhere
    return df.sort_index()


def insert_at(df: pd.DataFrame, sample_date: Any, values: Any) -> pd.DataFrame:
    """ Insert some values into a bi-temporal dataframe.
        This is like what would happen when we get a price correction.
    """
    observed_dt = dt(datetime.now())
    return multi_index_insert_row(df, [sample_date, observed_dt], values)
