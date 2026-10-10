"""Independent APF planning CLI. Never imports the Factory execution chain."""

VERSION = "0.1.0"
VERSION_TEXT = "AI Project Factory 0.1.0\nWit beyond measure is man's greatest treasure"


class APFError(Exception):
    """A user-facing failure that must not publish a successful plan."""
