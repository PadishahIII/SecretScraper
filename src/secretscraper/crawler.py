"""The facade interfaces to integrate crawler, filter, and handler"""

import asyncio
import logging
import queue
import threading
import traceback
import typing
from typing import Set
from urllib.parse import urlparse

import aiohttp
import dynaconf
import httpx
from aiohttp import ClientResponse
from httpx import AsyncClient

from secretscraper.coroutinue import AsyncPoolCollector, AsyncTask
from secretscraper.entity import URL, Secret, URLNode
from secretscraper.filter import URLFilter
from secretscraper.handler import Handler
from secretscraper.urlparser import URLParser

from .config import settings
from .exception import CrawlerException
from .util import Range

logger = logging.getLogger(__name__)


class Crawler:
    """Crawler interface"""

    def __init__(
        self,
        start_urls: list[str],
        # client: aiohttp.ClientSession,
        url_filter: URLFilter,
        parser: URLParser,
        handler: Handler,
        # allowed_status: list[Range] = None,
        max_page_num: int = 0,
        max_depth: int = 3,
        num_workers: int = 100,
        proxy: str = None,
        headers: dict = None,
        verbose: bool = False,
        timeout: float = 5,
        debug: bool = False,
        follow_redirects: bool = False,
    ):
        """

        :param start_urls: urls to start crawl from
        # :param client: aiohttp client
        :param url_filter: determine whether a url should be crawled
        :param parser: extract child url nodes from html
        :param handler: how to deal with the crawl result
        # :param allowed_status: filter response status. None for no filter
        :param max_page_num: max number of urls to crawl, 0 for no limit
        :param max_depth: max url depth, should greater than 0
        :param num_workers: worker number of the async pool
        :param proxy: http proxy
        :param verbose: whether to print exception detail
        :param timeout: timeout for aiohttp request
        """
        self.proxy = proxy
        self.start_urls = start_urls
        # self.client = client
        self.filter = url_filter
        self.parser = parser
        self.handler = handler
        self.max_page_num = max_page_num
        self.max_depth = max_depth
        self.num_workers = num_workers
        self.verbose = verbose
        self.timeout = timeout
        self.headers = headers
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        self.follow_redirects = follow_redirects

        self.visited_urls: Set[URLNode] = set()
        self.found_urls: Set[URLNode] = set()  # newly found urls
        self.working_queue: queue.Queue[URLNode] = queue.Queue()  # BP queue
        self.url_dict: dict[URLNode, set[URLNode]] = (
            dict()
        )  # url and all of its children url
        self.js_dict: dict[URLNode, set[URLNode]] = (
            dict()
        )  # url and all of its children js
        self.total_page: int = 0  # total number of pages found, include error pages
        self.url_secrets: dict[URLNode, set[Secret]] = (
            dict()
        )  # url and secrets found from it
        self._event_loop = asyncio.new_event_loop()
        # self.client: aiohttp.ClientSession = aiohttp.ClientSession(
        #     loop=self._event_loop
        # )  # assign event loop to client
        self.client: httpx.AsyncClient = AsyncClient(verify=False, proxies=self.proxy)
        self.close = threading.Event()  # whether the crawler is closed
        self.close.clear()
        self.pool: AsyncPoolCollector = AsyncPoolCollector.create_pool(
            num_workers=num_workers, queue_capacity=0, event_loop=self._event_loop
        )

    def start(self):
        """Start event loop"""
        try:
            self._event_loop.run_until_complete(self.main_task())
        except asyncio.CancelledError:
            pass  # ignore

    def close_all(self):
        """Close crawler, cancel all tasks"""
        try:
            self._event_loop.run_until_complete(self.clean())
        except asyncio.CancelledError:
            pass  # ignore

    async def main_task(self):
        """A wrapper"""
        try:
            await asyncio.gather(self.run(), self.consumer())
        except asyncio.CancelledError:
            return

    async def run(self):
        """Start the crawler"""
        try:

            # initialize with start_urls
            for url in self.start_urls:
                url_obj = urlparse(url)
                url_node = URLNode(url=url, url_object=url_obj, depth=0, parent=None)
                # self.found_urls.add(url_node)
                if self.filter.doFilter(url_node.url_object):
                    logger.debug(f"Target: {url}")
                    self.visited_urls.add(url_node)
                    self.working_queue.put(url_node)

            while True:
                if self.max_page_num > 0 and self.total_page >= self.max_page_num:
                    break
                if (
                    self.working_queue.empty()
                    and self.pool.is_finish
                    and self.pool.done_queue.empty()
                ):
                    break

                try:
                    url_node = self.working_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                if self.max_depth <= 0 or url_node.depth <= self.max_depth:
                    task = AsyncTask(self.process_one, url_node)
                    await self.pool.submit(task)
                logger.debug(
                    f"Total:{self.total_page}, Found:{len(self.found_urls)}, Depth:{url_node.depth}, Visited:{len(self.visited_urls)}, Secrets:{sum([len(secrets) for secrets in self.url_secrets.values()])}"
                )
            logger.debug(f"Crawler finished")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            raise CrawlerException("Unexpected Exception") from e
        finally:
            await self.clean()

    async def process_one(self, url_node: URLNode):
        """Fetch, extract url children and execute handler on result"""
        if self.max_page_num > 0 and self.total_page >= self.max_page_num:
            return
        logger.debug(f"Processing {url_node.url}")
        self.total_page += 1
        response = await self.fetch(url_node.url)
        if response is not None:  # and response.status == 200
            url_node.response_status = str(response.status_code)

            response_text: str = response.text
            # try:
            #     response_text: str = await response.text(
            #         encoding="utf8", errors="ignore"
            #     )
            # except TimeoutError:
            #     logger.error(f"Timeout while reading response from {url_node.url}")
            #     return
            # call handler and urlparser
            # extract secrets TODO: nonblocking extract
            await self.extract_secrets(url_node, response_text)
            # extract links TODO: nonblocking extract
            await self.extract_links_and_extend(url_node, response, response_text)
        else:
            # no extend on this branch
            logger.debug(f"No extend on {url_node.url}")
            return
        logger.debug(f"Finished processing {url_node.url}")

    async def extract_secrets(self, url_node: URLNode, response_text: str):
        """Extract secrets from response and store them in self.url_secrets"""
        logger.debug(f"Extracting secret from {url_node.url}")

        secrets = self.handler.handle(response_text)
        if secrets is not None:
            self.url_secrets[url_node] = set(secrets)
        logger.debug(f"Extract secret of number {len(list(secrets))} from {url_node}")

    async def extract_links_and_extend(
        self, url_node: URLNode, response: httpx.Response, response_text: str
    ):
        """Extract links from response and extend the task queue in demand
        This function only works if the response is text-like, but regardless of whether it is html or not.
        Extract and extend `url_node` only if `response` is text-like.
        """
        is_text_like = False
        is_html = False
        try:
            content_type = response.headers['content-type']
        except KeyError:
            content_type = ""
        if content_type.startswith("text"):
            is_text_like = True
            if content_type.strip().startswith("text/html"):
                is_html = True
        elif content_type.startswith("application"):
            if content_type.endswith(
                "octet-stream"
            ) or content_type.endswith("pdf"):
                is_text_like = False
            else:
                is_text_like = True

        if not is_text_like or not is_html:  # or not is_html just process html
            return
        if response.status_code != 200:  # just process normal response
            return

        if self.max_depth <= 0 or url_node.depth + 1 <= self.max_depth:
            # avoid enqueue urls with excessive depth
            # for non-html response, just record, no visit
            is_extending = True
        else:
            is_extending = False

        logger.debug(f"Extracting links from {url_node.url}")
        url_children: set[URLNode] = self.parser.extract_urls(url_node, response_text)
        if len(url_children) > 0:
            self.url_dict[url_node] = set()
        elif is_html and (
            url_node not in self.url_dict.keys() or self.url_dict[url_node] is None
        ):
            self.url_dict[url_node] = set()

        for child in url_children:
            if child is not None and child not in self.visited_urls:
                self.found_urls.add(child)
                if is_extending and self.filter.doFilter(child.url_object):
                    self.working_queue.put(child)
                    self.visited_urls.add(child)
                if child.url_object.path.endswith(
                    ".js"
                ) or child.url_object.path.endswith(".js.map"):
                    if url_node not in self.js_dict:
                        self.js_dict[url_node] = set()
                    self.js_dict[url_node].add(child)
                else:
                    self.url_dict[url_node].add(child)
                logger.debug(f"New link found: {child.url} from {url_node.url}")

    async def fetch(self, url: str) -> httpx.Response:
        """Wrapper for sending http request
        If exception occurs, return None
        """
        logger.debug(f"Fetching {url}")
        response = None
        try:
            # response = await self.client.get(
            #     url,
            #     allow_redirects=self.follow_redirects,
            #     headers=self.headers,
            #     proxy=self.proxy,
            #     verify_ssl=False,
            #     timeout=self.timeout,
            # )
            response = await self.client.get(
                url,
                headers=self.headers,
                follow_redirects=self.follow_redirects,
                timeout=self.timeout,
            )
            logger.debug(f"Fetch {url}, status: {response.status_code}")

        except TimeoutError:
            logger.error(f"Timeout while fetching {url}")
        except httpx.ConnectError as e:
            logger.error(f"Connection error for {url}: {e}")
        except httpx.InvalidURL as e:
            logger.error(f"Invalid URL for {url}: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout while fetching {url} ")
        except httpx.ReadError as e:
            logger.debug(f"Read error for {url}: {e}") # trigger when keyboard interrupt
        except KeyboardInterrupt:
            pass  # ignore
        except Exception as e:
            logger.error(f"Unexpected error: {e.__class__} while fetching {url}")
        return response

    async def clean(self):
        """Close pool, cancel tasks, close http client session"""
        try:
            await self.client.aclose()
        except:
            pass  # ignore
        try:
            await self.pool.close()
        except:
            pass  # ignore
        if not self.close.is_set():
            self.close.set()
        logger.debug(f"Closing")

    async def consumer(self):
        """Consume the result of pool"""
        async for future in self.pool.iter():
            if future.done():
                logger.debug(f"Done task for {future}")
                result = future.result()
                if future.exception() is not None:
                    try:
                        raise CrawlerException(
                            future.exception()
                        ) from future.exception()
                    except Exception as e:
                        if self.verbose:
                            logger.error(e)
                            logger.error(traceback.format_exc())
                        else:
                            logger.error(e)
                if self.close.is_set():
                    logger.debug(f"Closing Consumer")
                    return
