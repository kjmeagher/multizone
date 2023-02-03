<!--
SPDX-FileCopyrightText: © 2023 Kevin Meagher

SPDX-License-Identifier: GPL-3.0-or-later
-->

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/kjmeagher/multizone/main.svg)](https://results.pre-commit.ci/latest/github/kjmeagher/multizone/main)
[![Tests](https://github.com/kjmeagher/multizone/actions/workflows/tests.yml/badge.svg)](https://github.com/kjmeagher/multizone/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/kjmeagher/multizone/branch/main/graph/badge.svg?token=PS8PMZQZRZ)](https://codecov.io/gh/kjmeagher/multizone)

# multizone
Command line tool for calculating times in multiple different timezones.

Say that you want to schedule a zoom meeting at 15:30 New York time with people in then you can type the following to get 
```console
$ multizone 15:30 EST --zones US/Alaska Europe/Berlin Asia/Tokyo
Asia/Tokyo     Thu, 02 Feb, 2023 at 05:30 AM +0900
Europe/Berlin  Wed, 01 Feb, 2023 at 21:30 PM +0100
EST            Wed, 01 Feb, 2023 at 15:30 PM -0500
US/Central     Wed, 01 Feb, 2023 at 14:30 PM -0600
US/Alaska      Wed, 01 Feb, 2023 at 11:30 AM -0900
```
In addition, the local time zone is always included in the list of times.

See `multizone --help` for all the options. A toml configuration file can be placed in `~/.config/multizone/multizone.toml` to include
frequently used timezones, timezeone aliases, and time formatting. See the example in [multizone.example.toml](multizone.example.toml).
