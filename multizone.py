#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2023 Kevin Meagher
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command line tool for calculating times in multiple different timezones."""

from __future__ import annotations

__version__ = "0.1.0"

import argparse
import sys
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any, Dict

import tabulate
import tzlocal
from babel.core import default_locale
from babel.dates import format_datetime
from termcolor import colored
from xdg_base_dirs import xdg_config_home

if sys.version_info < (3, 9):
    from backports import zoneinfo
else:
    import zoneinfo
if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

ConfigType = Dict[str, Any]


def get_arg(time_str: str, sep: str) -> list[int]:
    """Parse date or time with 1 or two delimiters."""
    split = time_str.split(sep)
    if len(split) in (2, 3):
        return [int(x) for x in split]
    raise ValueError


def parse_time_arg(  # noqa: C901,PLR0912
    time_arg: list[str],
    default_time: datetime,
    default_zone: tzinfo,
) -> datetime:
    """Parse the date time an time zone arguments."""
    refdate = None
    reftime = None
    refzone: tzinfo | None = None

    for arg in time_arg:
        if refdate is None:
            try:
                refdate = get_arg(arg, "-")
                continue
            except ValueError:
                pass
            try:
                refdate = get_arg(arg, "/")
                continue
            except ValueError:
                pass
        if reftime is None:
            try:
                reftime = get_arg(arg, ":")
                continue
            except ValueError:
                pass
        if refzone is None:
            try:
                refzone = zoneinfo.ZoneInfo(arg)
                continue
            except zoneinfo.ZoneInfoNotFoundError:
                pass
        mesg = f'I don\'t understand argument "{arg}"'
        raise ValueError(mesg)

    if not refzone:
        refzone = default_zone
    ref_dt = default_time.astimezone(refzone)
    if refdate:
        if len(refdate) == 2:  # noqa: PLR2004
            refdate.insert(0, ref_dt.year)
    else:
        refdate = [ref_dt.year, ref_dt.month, ref_dt.day]

    if reftime:
        if len(reftime) == 2:  # noqa: PLR2004
            reftime.append(0)
    else:
        reftime = [ref_dt.hour, ref_dt.minute, ref_dt.second]

    return datetime(refdate[0], refdate[1], refdate[2], reftime[0], reftime[1], reftime[2], tzinfo=refzone)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments with argparse."""
    parser = argparse.ArgumentParser(description="Convert localtime to other timezones")
    parser.add_argument("time", nargs="*", help="Time to convert (Default: Now)")
    parser.add_argument("--config", help="Configuration file")
    parser.add_argument(
        "--format",
        "-f",
        help="Output format to use for times, same as used by strftime",
    )
    parser.add_argument("--zones", "-z", nargs="+", help="List of timezones to print out that time")
    parser.add_argument("--list", action="store_true", help="Print a list of all timezones and exit")
    parser.add_argument("-l", "--locale")
    args = parser.parse_args()

    if args.list:
        for avail_zones in sorted(zoneinfo.available_timezones()):
            print(avail_zones)  # noqa: T201
        sys.exit(0)
    return args


def load_config(config_path: Path | None) -> ConfigType:
    """Read toml configuration file from given path or default path."""
    if config_path is None:
        config_filename = xdg_config_home() / "multizone" / "multizone.toml"
        if not config_filename.is_file():
            config_filename = None
    else:
        config_filename = Path(config_path)
    if config_filename is not None:
        with config_filename.open("rb") as file_buff:
            return tomllib.load(file_buff)
    else:
        return {}


def configure(args: argparse.Namespace, config_file: ConfigType) -> ConfigType:
    """Get the configuration from the command line arguments and contents of config file."""
    config = {}

    if args.format:
        config["format"] = args.format
    else:
        config["format"] = config_file.get("format", "E, dd MMM, yyyy 'at' HH:mm a Z")

    if args.zones:
        config["zones"] = args.zones
    else:
        config["zones"] = config_file.get("zones", [])

    config["aliases"] = config_file.get("aliases", {})

    config["time"] = args.time

    config["reftime"] = {"color": None, "on_color": None, "attrs": []}
    config["reftime"].update(config_file.get("reftime", {}))

    config["localtime"] = {"color": None, "on_color": None, "attrs": []}
    config["localtime"].update(config_file.get("localtime", {}))

    if args.locale:
        config["locale"] = args.locale
    else:
        config["locale"] = config_file.get("locale", default_locale())

    return config


def time_offset(item: tuple[str, datetime]) -> timedelta:
    """Key function to sort times."""
    offset = item[1].utcoffset()
    assert offset is not None
    return -offset


def zone_table(
    timezones: list[str],
    aliases: dict[str, str],
    refdt: datetime,
    localzone: tzinfo,
) -> list[tuple[str, datetime]]:
    """Create a table of times for each time zone."""
    zones: list[tuple[str, datetime]] = []
    found_local = False
    found_ref = False
    localdt = refdt.astimezone(localzone)
    localoffset = localdt.utcoffset()
    refoffset = refdt.utcoffset()

    for zonename in timezones:
        name = aliases.get(zonename, zonename)
        zone = zoneinfo.ZoneInfo(zonename)
        time = refdt.astimezone(zone)
        if time.utcoffset() == localoffset:
            found_local = True
        if time.utcoffset() == refoffset:
            found_ref = True
        zones.append((name, time))

    if not found_local:
        zones.append((str(localzone), localdt))

    if not found_ref and localoffset != refoffset:
        tzname = refdt.tzname()
        assert tzname is not None
        zones.append((tzname, refdt))

    zones.sort(key=time_offset)
    return zones


def table_to_string(
    zones: list[tuple[str, datetime]],
    refdt: datetime,
    localzone: tzinfo,
    config: ConfigType,
) -> str:
    """Convert a table of times into a tabulated string to print."""
    zones2 = []
    for name, time in zones:
        timestr = format_datetime(time, config["format"], locale=config["locale"])
        new_name = name
        if time.utcoffset() == refdt.astimezone(localzone).utcoffset():
            new_name = colored(new_name, **config["localtime"])
            timestr = colored(timestr, **config["localtime"])
        if time.utcoffset() == refdt.utcoffset():
            new_name = colored(new_name, **config["reftime"])
            timestr = colored(timestr, **config["reftime"])
        zones2.append((new_name, timestr))

    return tabulate.tabulate(zones2, tablefmt="plain")


def main() -> None:  # pragma: no cover
    """Script entry point."""
    # get the current time and the machine's timezone
    utcnow = datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
    localzone = tzlocal.get_localzone()

    args = parse_args()
    config_file = load_config(args.config)

    # run configuration
    config = configure(args, config_file)

    # parse the time given at command line and localzone
    refdt = parse_time_arg(config["time"], utcnow, localzone)

    # create the actual table
    zones = zone_table(config["zones"], config["aliases"], refdt, localzone)

    # print the table
    print(table_to_string(zones, refdt, localzone, config))  # noqa: T201


if __name__ == "__main__":
    main()  # pragma: no cover
