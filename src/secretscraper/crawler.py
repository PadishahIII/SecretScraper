"""The facade interfaces to integrate crawler, filter, and handler"""
import asyncio
import logging
import queue
import typing
from typing import Set
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientResponse

from secretscraper.coroutinue import AsyncPoolCollector, AsyncTask
from secretscraper.entity import URL, Secret, URLNode
from secretscraper.filter import URLFilter
from secretscraper.handler import Handler
from secretscraper.urlparser import URLParser

from .exception import CrawlerException

logger = logging.getLogger(__name__)


class Crawler:
    """Crawler interface"""

    def __init__(self,
                 start_urls: list[str],
                 client: aiohttp.ClientSession,
                 url_filter: URLFilter,
                 parser: URLParser,
                 handler: Handler,
                 max_page_num: int = 0,
                 max_depth: int = 3,
                 num_workers: int = 100,
                 ):
        """

        :param start_urls: urls to start crawl from
        :param client: aiohttp client
        :param url_filter: determine whether a url should be crawled
        :param parser: extract child url nodes from html
        :param handler: how to deal with the crawl result
        :param max_page_num: max number of urls to crawl, 0 for no limit
        :param max_depth: max url depth, should greater than 0
        :param num_workers: worker number of the async pool
        """
        self.start_urls = start_urls
        self.client = client
        self.filter = url_filter
        self.parser = parser
        self.handler = handler
        self.max_page_num = max_page_num
        self.max_depth = max_depth
        self.num_workers = num_workers

        self.visited_urls: Set[URLNode] = set()
        self.found_urls: Set[URLNode] = set()  # newly found urls
        self.working_queue: queue.Queue[URLNode] = queue.Queue()  # BP queue
        self.url_dict: dict[URLNode, set[URLNode]] = dict()  # url and all of its children url
        self.total_page: int = 0  # total number of pages found
        self.url_secrets: dict[URLNode, set[Secret]] = dict()  # url and secrets found from it
        self._event_loop = asyncio.new_event_loop()
        self.pool: AsyncPoolCollector = AsyncPoolCollector.create_pool(
            num_workers=num_workers,
            queue_capacity=0,
            event_loop=self._event_loop
        )

    def start(self):
        """Start event loop"""
        self._event_loop.run_until_complete(self.run())

    async def run(self):
        """Start the crawler"""
        try:

            # initialize with start_urls
            for url in self.start_urls:
                url_obj = urlparse(url)
                url_node = URLNode(url=url, url_object=url_obj, depth=0, parent=None)
                # self.found_urls.add(url_node)
                self.visited_urls.add(url_node)
                self.working_queue.put(url_node)

            while True:
                if self.working_queue.empty() and self.pool.is_finish:
                    break

                try:
                    url_node = self.working_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                if url_node.depth <= self.max_depth:
                    task = AsyncTask(self.process_one, url_node)
                    await self.pool.submit(task)
        except Exception as e:
            await self.clean()
            raise CrawlerException("Unexpected Exception") from e

    async def process_one(self, url_node: URLNode):
        """Fetch, extract url children and execute handler on result"""
        response = await self.fetch(url_node.url)
        if response.status == 200 and response.content_type == 'text/html':
            # call handler and urlparser
            # extract secrets TODO: nonblocking extract
            response_text: str = await response.text(encoding="utf8", errors="ignore")
            secrets = self.handler.handle(response_text)
            if secrets is not None:
                self.url_secrets[url_node] = set(secrets)
            # extract links TODO: nonblocking extract
            url_children: set[URLNode] = self.parser.extract_urls(response_text)
            for child in url_children:
                if child is not None and child not in self.visited_urls:
                    self.found_urls.add(child)
                    self.working_queue.put(child)
        else:
            # no extend on this branch
            return
        logger.debug(f"Process_one {url_node.url} get response: {response.status} ")

    async def fetch(self, url: str) -> ClientResponse:
        """Wrapper for sending http request"""
        response = await self.client.get(url, allow_redirects=False)
        return response

    async def clean(self):
        """Close pool, cancel tasks, close http client session"""
        await self.client.close()
        await self.pool.close()
