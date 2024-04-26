"""Exceptions raised by SecretScraper."""


class SecretScraperException(Exception):
    """Global exception raised by SecretScraper"""

    pass


class AsyncPoolException(SecretScraperException):
    """Exception raised by coroutine module"""

    pass


class HandlerException(SecretScraperException):
    """Exception raised by handlers module"""

    pass


class CrawlerException(SecretScraperException):
    """Exception raised by crawler module"""

    pass


class FacadeException(SecretScraperException):
    """Exception raised by facade classes"""

    pass

class FileScannerException(SecretScraperException):
    """Exception raised by file scanner"""
    pass
