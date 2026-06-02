import datetime
from typing import Any, cast

from dateutil.parser import parse as _parse


def parse(string: str, agnostic: bool = False, **kwargs: Any) -> datetime.datetime:
    return cast(
        datetime.datetime, _parse(string, yearfirst=True, dayfirst=False, **kwargs)
    )
