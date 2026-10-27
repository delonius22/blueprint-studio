"""Errors that stop the agent from starting."""


class StartupError(Exception):
    """The agent refuses to start; the message names what is wrong."""
