import datetime
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import tzlocal


class TimezoneError(Exception):
    pass


def _get_localzone_name() -> str:
    """Return the local timezone name across supported tzlocal versions."""
    if hasattr(tzlocal, "get_localzone_name"):
        return tzlocal.get_localzone_name()

    local_zone = tzlocal.get_localzone()
    return getattr(local_zone, "zone", getattr(local_zone, "key", str(local_zone)))


def mktz(zone: str | None = None) -> datetime.tzinfo:
    """
    Return a new timezone (tzinfo object) based on the zone using the stdlib
    zoneinfo package.

    The concise name 'mktz' is for convenient when using it on the
    console.

    Parameters
    ----------
    zone : `String`
           The zone for the timezone. This defaults to local, returning:
           tzlocal.get_localzone()

    Returns
    -------
    An instance of a timezone which implements the tzinfo interface.

    Raises
    - - - - - -
    TimezoneError : Raised if a user inputs a bad timezone name.
    """
    if zone is None:
        zone = _get_localzone_name()

    if os.path.isabs(zone):
        zone = zone.rsplit("zoneinfo/", 1)[-1]

    try:
        return ZoneInfo(zone)
    except ZoneInfoNotFoundError:
        raise TimezoneError('Timezone "%s" can not be read' % (zone))
