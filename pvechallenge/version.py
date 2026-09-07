"""The version the interface displays.

A build stamps `_version.py` into the package, holding the version the executable
was published under. A source tree has no version to speak of: the module is
absent, and the interface says `dev` rather than inventing a number or repeating
one from `pyproject.toml` that a tagged build would contradict.
"""

#: Shown when no build stamped a version into the package.
DEV_VERSION = "dev"


def app_version() -> str:
    """Version to display, or `dev` when running from the sources."""
    try:
        from ._version import VERSION
    except ImportError:
        return DEV_VERSION
    return VERSION or DEV_VERSION
