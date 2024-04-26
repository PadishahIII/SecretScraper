"""Local file scanner, find secrets within local files"""
import logging
import mimetypes
import pathlib

from .entity import Secret
from .exception import FileScannerException
from .handler import Handler

logger = logging.getLogger(__name__)


class FileScanner:
    """Extract secrets from local files"""

    def __init__(
        self,
        targets: list[pathlib.Path],
        handler: Handler,
    ):
        """

        :param targets: target files to scan
        :param handler:
        :param verbose:
        """
        self.targets = targets
        self.handler = handler

        self.secrets: dict[pathlib.Path, set[Secret]] = {}

    def start(self):
        """Start scanning"""

        for file in self.targets:
            if not file.exists():
                raise FileScannerException(f"Fail to open {file.name}")
            if not file.is_file():
                raise FileScannerException(f"Internal error: got a directory: {file.name}")
            # pass non-text file
            content: str = file.read_text(encoding="utf8", errors="ignore")
            logger.debug(f"Read file content: {len(content)}bytes from {file.name}")
            secrets: set[Secret] = set(list(self.handler.handle(content)))
            if len(secrets) > 0:
                self.secrets[file] = secrets
                logger.debug(f"Found {len(secrets)} secrets from {file.name}")
