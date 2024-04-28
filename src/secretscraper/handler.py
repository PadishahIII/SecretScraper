"""Handler module for extracting data from HTML pages and other text files crawled from website"""

import queue
import re
import sys
import typing
from typing import Protocol

from bs4 import BeautifulSoup, NavigableString, Tag

from secretscraper.entity import Secret
from secretscraper.exception import HandlerException

# T = typing.TypeVar("T")
# IterableAsyncOrSync: typing.TypeAlias = typing.Iterable[T] | typing.AsyncIterable[T]
BSResult = Tag | NavigableString | None


class Handler(Protocol):
    """Base class for different types of handlers"""

    def handle(self, text: str) -> typing.Iterable[Secret]: ...


class ReRegexHandler(Handler):
    """ Regex handler using the `re` module, simple but have lowest performance."""

    def __init__(self, rules: dict[str, str], flags: int = 0):
        """

        :param rules: rules dictionary with keys indicating type and values indicating the regex
        """
        self.types = list(rules.keys())
        regexes = list(rules.values())
        self.regexes: list[re.Pattern] = list()
        for regex in regexes:
            self.regexes.append(re.compile(regex, flags=flags | re.IGNORECASE))

    def handle(self, text: str) -> typing.Iterable[Secret]:
        """Extract secret data"""
        result_list: list[Secret] = list()
        for index, regex in enumerate(self.regexes):
            # match = regex.search(text)
            # if match is not None:
            #     secret_data = match.group(0)
            #     secret_type = self.types[index]
            #     secret = Secret(type=secret_type, data=secret_data)
            #     result_list.append(secret)
            matches = regex.findall(text)
            for match in matches:
                if match is not None:
                    secret_data = match if type(match) is not tuple else match[0]
                    secret_type = self.types[index]
                    secret = Secret(type=secret_type, data=secret_data)
                    result_list.append(secret)
        return result_list


if not sys.platform.startswith("win"):
    # hyperscan does not support windows
    import hyperscan


    class HyperscanRegexHandler(Handler):
        """Regex handler using `hyperscan` module"""

        def __init__(
            self, rules: dict[str, str], lazy_init: bool = False, hs_flag: int = 0
        ):
            """

            :param rules: regex rules dictionary with keys indicating type and values indicating the regex
            :param lazy_init: True for deferring the initialization to actively call the init() method, otherwise initialize immediately
            :param hs_flag: hyperscan flag perform to every expressions
            """
            # self.output_queue: queue.Queue[Secret] = queue.Queue()
            self.rules = rules
            self._init: bool = False
            self._hs_flag: int = (
                hs_flag | hyperscan.HS_FLAG_SOM_LEFTMOST | hyperscan.HS_FLAG_CASELESS
            )
            self._db: typing.Optional[hyperscan.Database] = None
            self.patterns: dict[int, bytes] = dict()  # pattern id => regex in bytes
            self.types: dict[int, str] = dict()  # pattern id => type
            if not lazy_init:
                self.init()

        def init(self):
            """Initialize the hyperscan database."""
            self._db = hyperscan.Database()
            flags: list[int] = [self._hs_flag for _ in range(len(self.rules))]
            for index, type_str in enumerate(self.rules):
                regex = self.rules.get(type_str)
                self.patterns[index] = regex.encode("utf-8")
                self.types[index] = type_str

            self._db.compile(
                expressions=list(self.patterns.values()),
                ids=list(self.patterns.keys()),
                elements=len(self.patterns),
                flags=flags,
            )

            self._init = True

        def handle(self, text: str) -> typing.Iterable[Secret]:
            """Extract secret data via the pre-compiled hyperscan database

            This method is IO-bound.
            """
            if not self._init:
                raise HandlerException("Hyperscan database is not initialized")

            results: list[Secret] = list()

            def on_match(
                id: int,
                froms: int,
                to: int,
                flags: int,
                context: typing.Optional[typing.Any] = None,
            ) -> typing.Optional[bool]:
                match = text[froms:to]
                type = self.types.get(id)
                results.append(Secret(type, data=match))
                return None

            self._db.scan(
                text.encode("utf8"), match_event_handler=on_match
            )  # block call until all regex operation finish
            return results


class BSHandler(Handler):
    """BeautifulSoup handler that filter html elements on demand"""

    def __init__(
        self, filter_func: typing.Callable[[BeautifulSoup], list[BSResult]]
    ) -> None:
        self.filter = filter_func

    def handle(self, text: str) -> typing.Iterable[Secret]:
        """Extract secret data via filter

        :type text: str
        :param text: should be in html format
        """
        soup = BeautifulSoup(text, "html.parser")
        result: list[BSResult] = self.filter(soup)
        results: list[Secret] = list()
        if result is not None:
            secret = Secret(type="HTML Element", data=result)
            results.append(secret)
        return results


def get_regex_handler(rules: dict[str, str], type_: str = "", *args, **kwargs) -> Handler:
    """Return regex handler on current platform"""
    if len(type_) == 0:
        if sys.platform.startswith("win"):
            return ReRegexHandler(rules, *args, **kwargs)
        else:
            return HyperscanRegexHandler(rules, *args, **kwargs)
    else:
        if type == "regex":
            return ReRegexHandler(rules, *args, **kwargs)
        elif type == "hyperscan":
            return HyperscanRegexHandler(rules, *args, **kwargs)
        else:
            return ReRegexHandler(rules, *args, **kwargs)
