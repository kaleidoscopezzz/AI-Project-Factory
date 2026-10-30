"""APF product version and public error type; metadata imports no execution chain."""

VERSION = "1.0.0"
VERSION_TEXT = f"AI Project Factory {VERSION}\nWit beyond measure is man's greatest treasure"


class APFError(Exception):
    """A user-facing failure that must not publish a successful plan."""
