#!/usr/bin/env python3

# SPDX-FileCopyrightText: © 2023 Kevin Meagher
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for multizone."""

import contextlib
import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from babel.core import default_locale

import multizone

if sys.version_info < (3, 9):
    from backports.zoneinfo import ZoneInfo
else:
    from zoneinfo import ZoneInfo


def test_parse_time_args() -> None:
    """Tests parse_time_args()."""
    utc = ZoneInfo("UTC")
    time0 = datetime(2023, 1, 1, 00, 00, 00, tzinfo=utc)

    # parse the time given at command line and localzone
    time1 = multizone.parse_time_arg(["3:30"], time0, utc)
    assert time1.year == time0.year
    assert time1.month == time0.month
    assert time1.day == time0.day
    assert time1.hour == 3
    assert time1.minute == 30
    assert time1.tzinfo == time0.tzinfo

    time2 = multizone.parse_time_arg(["4/26"], time0, utc)
    assert time2.year == time0.year
    assert time2.month == 4
    assert time2.day == 26
    assert time2.hour == time0.hour
    assert time2.minute == time0.minute
    assert time2.tzinfo == time0.tzinfo

    time2 = multizone.parse_time_arg(["7-12"], time0, utc)
    assert time2.year == time0.year
    assert time2.month == 7
    assert time2.day == 12
    assert time2.hour == time0.hour
    assert time2.minute == time0.minute
    assert time2.tzinfo == time0.tzinfo

    time3 = multizone.parse_time_arg(["Asia/Tokyo"], time0, utc)
    assert time3.year == time0.year
    assert time3.month == time0.month
    assert time3.day == time0.day
    assert time3.hour == 9
    assert time3.minute == time0.minute
    assert time3.tzinfo == ZoneInfo("Asia/Tokyo")

    with pytest.raises(ValueError, match="ASDF"):
        multizone.parse_time_arg(["ASDF"], time0, utc)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="older versions of mock can't patch sys.argv")
def test_parse_args() -> None:
    """Test parse_args()."""
    with patch("sys.argv", ["multizone", "--list"]), contextlib.redirect_stdout(None):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            multizone.parse_args()
        assert pytest_wrapped_e.type is SystemExit

    iargs = [
        "multizone",
        "7/21",
        "3:30",
        "US/Eastern",
        "--config=asdf.toml",
        "--zones",
        "a",
        "b",
        "c",
        "--locale=en_US",
        "--format",
        "%H:%M",
    ]
    with patch("sys.argv", iargs):
        args = multizone.parse_args()
        assert args.time == ["7/21", "3:30", "US/Eastern"]
        assert args.config == "asdf.toml"
        assert args.zones == ["a", "b", "c"]
        assert args.list is False
        assert args.format == "%H:%M"


def test_load_config() -> None:
    """Test load_config()."""
    with patch.multiple(
        "pathlib.Path",
        open=mock_open(read_data=b""),
        is_file=MagicMock(return_value=False),
    ):
        assert multizone.load_config(None) == {}

    with patch.multiple(
        "pathlib.Path",
        open=mock_open(read_data=b"time=1984"),
        is_file=MagicMock(return_value=True),
    ):
        assert multizone.load_config(None) == {"time": 1984}

    with patch("pathlib.Path.open", mock_open(read_data=b"format = '%h:%m'")):
        assert multizone.load_config(Path("ASDF")) == {"format": "%h:%m"}


def test_configure() -> None:
    """Test configure()."""
    args1 = Namespace(format=None, zones=None, locale=None, time=None)
    args2 = Namespace(format="HH:mm", zones=["UTC"], locale="de_DE", time="3:30")
    cfg = {
        "format": "H:m",
        "zones": ["ROK", "ROC"],
        "aliases": {"ROK": "Korea"},
        "reftime": {"color": "red"},
        "localtime": {"color": "green"},
        "locale": "fr_FR",
    }

    assert multizone.configure(args1, cfg) == {
        "format": "H:m",
        "zones": ["ROK", "ROC"],
        "aliases": {"ROK": "Korea"},
        "time": None,
        "reftime": {"color": "red", "on_color": None, "attrs": []},
        "localtime": {"color": "green", "on_color": None, "attrs": []},
        "locale": "fr_FR",
    }
    assert multizone.configure(args2, cfg) == {
        "format": "HH:mm",
        "zones": ["UTC"],
        "aliases": {"ROK": "Korea"},
        "time": "3:30",
        "reftime": {"color": "red", "on_color": None, "attrs": []},
        "localtime": {"color": "green", "on_color": None, "attrs": []},
        "locale": "de_DE",
    }

    assert multizone.configure(args1, {}) == {
        "format": "E, dd MMM, yyyy 'at' HH:mm a Z",
        "zones": [],
        "aliases": {},
        "time": None,
        "reftime": {"color": None, "on_color": None, "attrs": []},
        "localtime": {"color": None, "on_color": None, "attrs": []},
        "locale": default_locale(),
    }


def test_zone_table() -> None:
    """Test zone_table()."""
    utc = ZoneInfo("UTC")
    rok = ZoneInfo("ROK")
    est = ZoneInfo("EST")
    time0 = datetime(2023, 1, 1, 00, 00, 00, tzinfo=utc)
    time_rok = time0.astimezone(rok)
    time_est = time0.astimezone(est)
    tab1 = multizone.zone_table([], {}, time0, utc)
    assert tab1 == [("UTC", time0)]

    tab2 = multizone.zone_table([], {}, time0, rok)
    assert tab2 == [("ROK", time_rok), ("UTC", time0)]

    tab3 = multizone.zone_table(["ROK", "EST", "UTC"], {}, time0, rok)
    assert tab3 == [("ROK", time_rok), ("UTC", time0), ("EST", time_est)]

    tab4 = multizone.zone_table(["ROK", "EST", "UTC"], {"ROK": "Korea", "EST": "Eastern"}, time0, rok)
    assert tab4 == [("Korea", time_rok), ("UTC", time0), ("Eastern", time_est)]


def test_table_to_string() -> None:
    """Test table_to_string()."""
    utc = ZoneInfo("UTC")
    rok = ZoneInfo("ROK")
    time0 = datetime(2023, 1, 1, 00, 00, 00, tzinfo=utc)
    time_rok = time0.astimezone(rok)
    tttt = [("Korea", time_rok), ("UTC", time0)]
    config = {"format": "HH:mm", "locale": "en_US", "localtime": {}, "reftime": {}}
    output = multizone.table_to_string(tttt, time_rok, utc, config).split("\n")
    assert "Korea" in output[0]
    assert "09:00" in output[0]
    assert "UTC" in output[1]
    assert "00:00" in output[1]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
