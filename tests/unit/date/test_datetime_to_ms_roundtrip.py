import datetime
from zoneinfo import ZoneInfo

import pytest

from arctic.date import mktz, datetime_to_ms, ms_to_datetime


def assert_roundtrip(tz):
    ts = datetime.datetime(1982, 7, 1, 16, 5)

    ts1 = ts.replace(tzinfo=tz)
    ts2 = ms_to_datetime(datetime_to_ms(ts1.astimezone(mktz("UTC"))), tz)

    assert(ts2.hour == ts1.hour)
    assert ts2 == ts1


def get_tz():
    tz = ZoneInfo("Europe/London")
    tmp = ms_to_datetime(0, tz)
    tz = tmp.tzinfo
    return tz


def test_UTC_roundtrip():
    tz = ZoneInfo("UTC")
    assert_roundtrip(tz)


def test_weird_get_tz_local():
    tz = get_tz()
    assert_roundtrip(tz)


def test_zoneinfo_London():
    tz = ZoneInfo("Europe/London")
    assert_roundtrip(tz)


def test_mktz_London():
    tz = mktz("Europe/London")
    assert_roundtrip(tz)


def test_datetime_roundtrip_local_no_tz():
    pdt = datetime.datetime(2012, 6, 12, 12, 12, 12, 123000)
    pdt2 = ms_to_datetime(datetime_to_ms(pdt)).replace(tzinfo=None)
    assert pdt2 == pdt

    pdt = datetime.datetime(2012, 1, 12, 12, 12, 12, 123000)
    pdt2 = ms_to_datetime(datetime_to_ms(pdt)).replace(tzinfo=None)
    assert pdt2 == pdt


def test_datetime_roundtrip_local_tz():
    pdt = datetime.datetime(2012, 6, 12, 12, 12, 12, 123000, tzinfo=mktz())
    pdt2 = ms_to_datetime(datetime_to_ms(pdt))
    assert pdt2 == pdt

    pdt = datetime.datetime(2012, 1, 12, 12, 12, 12, 123000, tzinfo=mktz())
    pdt2 = ms_to_datetime(datetime_to_ms(pdt))
    assert pdt2 == pdt


def test_datetime_roundtrip_est_tz():
    pdt = datetime.datetime(2012, 6, 12, 12, 12, 12, 123000, tzinfo=mktz('EST'))
    pdt2 = ms_to_datetime(datetime_to_ms(pdt))
    assert pdt2.replace(tzinfo=mktz()) == pdt

    pdt = datetime.datetime(2012, 1, 12, 12, 12, 12, 123000, tzinfo=mktz('EST'))
    pdt2 = ms_to_datetime(datetime_to_ms(pdt))
    assert pdt2.replace(tzinfo=mktz()) == pdt


@pytest.mark.parametrize("microseconds,expected", [
    (807000, 1074069004807),
    (807243, 1074069004807),
    (807675, 1074069004807)
])
def test_millisecond_conversion(microseconds, expected):
    pdt = datetime.datetime(2004, 1, 14, 8, 30, 4, microseconds, tzinfo=ZoneInfo("UTC"))
    pdt2 = datetime_to_ms(pdt)
    assert pdt2 == expected
