"""Facade classes"""

import copy
import functools
import logging
import pathlib
import traceback
import typing
import warnings
from urllib.parse import urlparse
from collections import namedtuple

import click
import dynaconf

from .crawler import Crawler
from .exception import FacadeException, FileScannerException
from .filter import (ChainedURLFilter, DomainBlackListURLFilter,
                     DomainWhiteListURLFilter)
from .handler import get_regex_handler
from .output_formatter import Formatter
from .scanner import FileScanner
from .urlparser import URLParser, RegexURLParser
from .util import Range, read_rules_from_setting, to_host_port

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")  # ignore all warnings


def print_func(f: typing.IO, func: typing.Callable, content: str, **kwargs) -> None:
    func(content, **kwargs)
    func(content, file=f, **kwargs)


def print_func_colorful(
    f: typing.IO,
    func: typing.Callable,
    content: str,
    fg: str = None,
    bg: str = None,
    blink=False,
    bold=False,
):
    print_func(f,
               func,
               click.style(content, fg=fg, bg=bg, blink=blink, bold=bold)
               )


print_config = functools.partial(click.secho, fg="bright_black", bold=True)


class CrawlerFacade:
    """Crawler facade"""

    def __init__(
        self,
        full_settings: dynaconf.Dynaconf,
        custom_settings: dict,
        print_func: typing.Callable[[str], ...] = print,
    ) -> None:
        """

        :param full_settings: dynaconf.Dynaconf
        :param custom_settings: dict
        :param print_func: must be partial of click.echo()
        """
        self.settings = full_settings
        self.custom_settings = custom_settings
        self.formatter = Formatter()
        self.hide_regex: bool = False
        self.outfile = pathlib.Path(__file__).parent / "crawler.log"
        self.print_func = print_func
        self.debug: bool = False
        self.follow_redirects: bool = False
        self.detail_output: bool = False
        self.crawler: Crawler = self.create_crawler()

    def start(self):
        """Start the crawler and output"""
        with self.outfile.open("w") as f:
            try:

                # print_func(f"Starting crawler...")
                print_func_colorful(f,
                                    self.print_func,
                                    f"Target URLs: {', '.join(self.crawler.start_urls)}",
                                    bold=True,
                                    blink=True,
                                    )
                self.crawler.start()
                if self.detail_output:
                    # print_func_colorful(self.print_func,f"Total page: {self.crawler.total_page}")
                    self.formatter.output_url_hierarchy(self.crawler.url_dict, True)

                    if not self.hide_regex:
                        print_func_colorful(f, self.print_func,
                                            f"{self.formatter.output_secrets(self.crawler.url_secrets)}"
                                            )
                    print_func_colorful(f, self.print_func, f"{self.formatter.output_js(self.crawler.js_dict)}")
                    self.formatter.output_found_domains(list(self.crawler.found_urls), True)
                else:
                    # tidy output
                    # URLs per domain
                    domains = set()
                    for url in self.crawler.start_urls:
                        try:
                            obj = urlparse(url)
                            domain, _ = to_host_port(obj.netloc)
                            if len(domain) > 0:
                                domains.add(domain.strip())
                        except:
                            pass
                    self.formatter.output_url_per_domain(domains, self.crawler.url_dict)
                    # JS per domain
                    self.formatter.output_url_per_domain(domains, self.crawler.js_dict, "JS")
                    # Domains
                    self.formatter.output_found_domains(list(self.crawler.found_urls), True)
                    # Secrets
                    if not self.hide_regex:
                        print_func_colorful(f, self.print_func,
                                            f"{self.formatter.output_secrets(self.crawler.url_secrets)}"
                                            )
            except KeyboardInterrupt:
                self.print_func("\nExiting...")
                self.crawler.close_all()
            except Exception as e:
                self.print_func(f"Unexpected error: {e}.\nExiting...")
                self.crawler.close_all()
                # raise FacadeException from e

    def create_crawler(self) -> Crawler:
        """Create a Crawler"""
        # Follow redirects
        if self.custom_settings.get("follow_redirects", False) is True:
            self.settings["follow_redirects"] = True
        # Hide regex output
        if self.custom_settings.get("hide_regex", False) is True:
            self.hide_regex = True
        # Get url filter
        allow_domains: str = self.custom_settings.get("allow_domains", "")
        disallow_domains: str = self.custom_settings.get("disallow_domains", "")
        if len(allow_domains) > 0:
            urlfilter = ChainedURLFilter(
                [
                    DomainWhiteListURLFilter(
                        {domain.strip() for domain in allow_domains.split(",")}
                    ),
                    DomainBlackListURLFilter(
                        {domain.strip() for domain in disallow_domains.split(",")}
                    ),
                ]
            )
        else:
            urlfilter = ChainedURLFilter(
                [
                    DomainBlackListURLFilter(
                        {domain.strip() for domain in disallow_domains.split(",")}
                    )
                ]
            )

        # Build start urls
        url_file: typing.Optional[pathlib.Path] = self.custom_settings.get(
            "url_file", None
        )
        url: typing.Optional[str] = self.custom_settings.get("url", None)
        start_urls = set()
        if url is None and url_file is None:
            raise FacadeException(f"One of '-u' and '-f' must be provided")
        if url_file is not None:
            with url_file.open("r") as f:
                lines = f.readlines()
                for line in lines:
                    if len(line.strip()) == 0:
                        continue
                    start_urls.add(line.strip())
        if url is not None:
            start_urls.add(url.strip())
        print_config(f"Target urls num: {len(start_urls)}")

        # Specify mode
        mode: typing.Optional[int] = self.custom_settings.get("mode", None)
        if mode is not None:
            mode = int(mode)
            if mode == 1:
                self.settings.max_depth = 1
            elif mode == 2:
                self.settings.max_depth = 2

        # Max depth, max page num
        max_page: typing.Optional[int] = self.custom_settings.get("max_page", None)
        max_depth: typing.Optional[int] = self.custom_settings.get("max_depth", None)
        if max_page is not None:
            self.settings.max_page_num = max_page
        if max_depth is not None:
            self.settings.max_depth = max_depth
        print_config(
            f"Max depth: {self.settings['max_depth']}, Max page num: {self.settings['max_page_num']}",
        )

        # Outfile
        outfile: typing.Optional[pathlib.Path] = self.custom_settings.get(
            "outfile", None
        )
        if outfile is not None:
            self.outfile = outfile
        print_config(f"Output file: {self.outfile}")

        # Status filter
        status: typing.Optional[str] = self.custom_settings.get("status", None)
        allowed_status: typing.Optional[list[Range]] = None
        if status is not None:
            for status_ex in status.split(","):
                status_ex = status_ex.strip()
                if status_ex.__contains__("-"):
                    min_status = status_ex.split("-")[0]
                    max_status = status_ex.split("-")[1]
                    if min_status >= max_status:
                        raise FacadeException(f"Invalid status range: {status_ex}")
                    if allowed_status is None:
                        allowed_status = list()
                    allowed_status.append(
                        Range(start=int(min_status), end=int(max_status) + 1)
                    )
                else:
                    if allowed_status is None:
                        allowed_status = list()
                    allowed_status.append(
                        Range(start=int(status_ex), end=int(status_ex) + 1)
                    )
        self.formatter._allowed_status = allowed_status

        # UA and Headers
        headers = self.settings.get("headers")
        ua: typing.Optional[str] = self.custom_settings.get("ua", None)
        if ua is not None:
            headers["User-Agent"] = ua.strip()
        cookie: typing.Optional[str] = self.custom_settings.get("cookie", None)
        if cookie is not None:
            headers["Cookie"] = cookie.strip()

        # Proxy
        proxy: typing.Optional[str] = self.custom_settings.get("proxy", None)
        if proxy is not None:
            self.settings["proxy"] = proxy.strip()
            print_config(f"Using proxy {proxy}")

        # Verbose
        verbose: typing.Optional[bool] = self.custom_settings.get("verbose", None)
        if verbose is not None:
            self.settings["verbose"] = verbose

        # Read rules from config file
        rules: dict[str, str] = read_rules_from_setting(self.settings)
        handler = get_regex_handler(rules)

        # Read url/js regex
        rules: list[str] = self.settings.get("urlFind")
        rules.extend(self.settings.get("jsFind"))
        rules_dict = {f"urlFinder_{i}": rule for i, rule in enumerate(rules)}
        parser = RegexURLParser(get_regex_handler(rules_dict, type_="regex"))

        # Detailed output
        if self.custom_settings.get("detail", False) is True:
            self.detail_output = True

        # Dangerous paths
        dangerous_paths: list[str] = list()
        if self.settings.get("dangerousPath", None) is not None:
            dangerous_paths.extend(set(self.settings("dangerousPath")))

        crawler = Crawler(
            start_urls=list(start_urls),
            url_filter=urlfilter,
            # parser=URLParser(),
            parser=parser,
            handler=handler,
            max_page_num=self.settings.get("max_page_num"),
            max_depth=self.settings.get("max_depth"),
            num_workers=self.settings.get("workers_num"),
            proxy=self.settings.get("proxy"),
            headers=headers,
            verbose=self.settings.get("verbose"),
            timeout=self.settings.get("timeout"),
            debug=self.debug,
            follow_redirects=self.settings["follow_redirects"],
            dangerous_paths = dangerous_paths
        )
        return crawler


class FileScannerFacade:
    """Facade for local file scanner"""

    def __init__(
        self,
        full_settings: dynaconf.Dynaconf,
        custom_settings: dict,
        print_func: typing.Callable[[str], ...] = print,
    ):
        self.settings = full_settings
        self.custom_settings = custom_settings
        self.print_func = print_func
        self.outfile = pathlib.Path(__file__).parent / "scanner.log"

        self.formatter = Formatter()
        self.scanner = self.init()

    def start(self):
        """Start file scanner"""
        with open(self.outfile, "w") as f:
            try:
                print_func_colorful(f, self.print_func, f"Targets: {len(self.scanner.targets)}", bold=True)
                self.scanner.start()

                result = self.formatter.output_local_scan_secrets(self.scanner.secrets)
                f.write(result)

            except FileScannerException as e:
                print_func_colorful(f, self.print_func,
                                    f"Exception while scanning file: {e}\nTraceback: {traceback.format_exc()}",
                                    fg="red")
            except KeyboardInterrupt:
                print_func_colorful(f, self.print_func, f"\nExiting")
            except Exception as e:
                print_func_colorful(f, self.print_func,
                                    f"Unexpected error: {e}.\nTraceback: {traceback.format_exc()}\n Exiting...")

    def init(self) -> FileScanner:
        """Initialize options"""
        # Verbose
        verbose: typing.Optional[bool] = self.custom_settings.get("verbose", None)
        if verbose is not None:
            self.settings["verbose"] = verbose

        # Outfile
        outfile: typing.Optional[pathlib.Path] = self.custom_settings.get(
            "outfile", None
        )
        if outfile is not None:
            self.outfile = outfile
        print_config(f"Output file: {self.outfile}")

        # Read rules from config file
        rules: dict[str, str] = read_rules_from_setting(self.settings)
        handler = get_regex_handler(rules)

        # Get all files from directory
        base: typing.Optional[pathlib.Path] = self.custom_settings.get('local', None)
        if base is None:
            raise FacadeException(f"Internal error: No base directory")
        targets: list[pathlib.Path] = list()
        if base.is_file():
            targets.append(base)
        else:
            for path in base.rglob("*"):
                if path.is_file():
                    targets.append(path)

        # Create file scanner
        file_scanner = FileScanner(
            targets=targets,
            handler=handler
        )
        return file_scanner
