"""Exceptions raised by SecretScraper."""


class SecretScraperException(Exception):
    """Global exception raised by SecretScraper"""

    pass


class AsyncPoolException(SecretScraperException):
    """Exception raised by coroutine module"""

    pass
