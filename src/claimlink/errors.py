"""Warnings and exceptions raised by ClaimLink."""


class ClaimLockError(Exception):
    """The claim lock file is unreadable, malformed, or has an unexpected shape."""


class ClaimExportError(Exception):
    """Claims could not be exported to LaTeX."""


class ClaimValueChangedWarning(UserWarning):
    """A claim's value changed since it was last registered."""


class ClaimLocationChangedWarning(UserWarning):
    """A claim was registered from a location other than its canonical one."""


class ClaimLocationUnavailableWarning(UserWarning):
    """A claim's source location could not be fully determined."""
