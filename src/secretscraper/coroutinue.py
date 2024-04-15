"""Asynchronous Python client"""

import asyncio
import logging
import threading
import typing
from dataclasses import dataclass, field
from typing import Callable

from secretscraper.exception import AsyncPoolException, SecretScraperException

logger = logging.getLogger(__name__)


@dataclass
class AsyncTask:
    def __init__(self, func: typing.Callable, *args, **kwargs):
        self.func = func
        self.future: asyncio.Future = asyncio.Future()
        self.args = args
        self.kwargs = kwargs


class AsyncWorker:
    """Consumer class"""

    def __init__(
        self,
        task_queue: asyncio.Queue[AsyncTask],
        event_loop: asyncio.AbstractEventLoop,
    ):
        self.task_queue = task_queue
        self.event_loop = event_loop
        self.is_running: bool = False
        self.future: asyncio.Future = asyncio.Future()

    def start(self):
        """Start consumer"""
        self.future = self.event_loop.create_task(self.run())

    async def stop(self, timeout: float = 0):
        """Stop consumer with an optional timeout"""
        try:
            await asyncio.wait_for(self.future, timeout)
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError:
            pass
        finally:
            self.is_running = False

    async def run(self):
        """Run consumer"""
        while True:
            try:
                task = await self.task_queue.get()
            except asyncio.CancelledError:
                break
            try:
                self.is_running = True
                ret = await task.func(*task.args, **task.kwargs)
                task.future.set_result(ret)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not task.future.done():
                    try:
                        raise AsyncPoolException(f"{e.__class__}:{e}") from e
                    except AsyncPoolException as ex:
                        task.future.set_exception(ex)
            finally:
                self.is_running = False


class AsyncPool:
    """Pool of AsyncWorkers"""

    def __init__(
        self,
        num_workers: int,
        event_loop: asyncio.AbstractEventLoop,
        queue_capacity: int = 1000,
    ):
        self.event_loop = event_loop
        self.workers: list[AsyncWorker] = []
        self.num_workers: int = num_workers
        self.queue_capacity: int = queue_capacity
        self.task_queue: asyncio.Queue[AsyncTask] = asyncio.Queue(
            maxsize=self.queue_capacity
        )

        self.start()

    def start(self):
        """Start all workers"""
        for _ in range(self.num_workers):
            self.workers.append(AsyncWorker(self.task_queue, self.event_loop))
        [worker.start() for worker in self.workers]
        # self.event_loop.run_forever()

    async def submit(self, task: AsyncTask) -> asyncio.Future:
        """Submit one task"""
        await self.task_queue.put(task)
        return task.future

    async def submit_all(self, tasks: list[AsyncTask]) -> list[asyncio.Future]:
        """Submit multiple tasks"""
        futures: list[asyncio.Future] = []
        for task in tasks:
            await self.submit(task)
            futures.append(task.future)
        return futures

    async def shutdown(
        self, timeout: float = 0, cancel_queue: bool = False, cancel_tasks: bool = True
    ) -> None:
        """Shutdown all workers, cancel un-done tasks optionally"""
        await asyncio.gather(*[worker.stop(timeout) for worker in self.workers])

        while True:
            try:
                task = self.task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if cancel_queue and not task.future.done():
                task.future.cancel()

        if cancel_tasks:
            for task in asyncio.all_tasks(loop=self.event_loop):
                task.cancel()
        # await asyncio.sleep(0.1)
        # self.event_loop.stop()
        logger.debug(f"Pool closing")

    @property
    def is_finish(self) -> bool:
        """Check if all workers are idle and task queue is empty"""
        return (
            not any(worker.is_running for worker in self.workers)
            and self.task_queue.empty()
        )


class AsyncPoolCollector:
    """Collect futures generated from pool"""

    def __init__(self, pool: AsyncPool, cancel_tasks: bool = True):
        self.pool: AsyncPool = pool
        self.cancel_tasks: bool = cancel_tasks  # whether cancel all tasks when shutdown
        self.done_queue: asyncio.Queue[asyncio.Future] = asyncio.Queue()
        self.closed = threading.Event()  # whether the pool is closed
        self.closed.clear()

    @staticmethod
    def create_pool(
        num_workers: int,
        queue_capacity: int,
        event_loop: asyncio.AbstractEventLoop,
        cancel_tasks: bool = True,
    ):
        """Factory function for creating AsyncPoolCollector
        :param queue_capacity: maximum size of task queue, 0 for infinite queue
        :return: AsyncPoolCollector
        """
        pool = (
            AsyncPool(num_workers, event_loop, queue_capacity)
            if event_loop
            else AsyncPool(num_workers, asyncio.new_event_loop(), queue_capacity)
        )
        return AsyncPoolCollector(pool, cancel_tasks)

    async def submit(self, task: AsyncTask) -> asyncio.Future:
        """Submit one task"""
        future = await self.pool.submit(task)
        future.add_done_callback(self.done_queue.put_nowait)
        return future

    async def submit_all(self, tasks: list[AsyncTask]) -> list[asyncio.Future]:
        """Submit multiple tasks"""
        futures = await self.pool.submit_all(tasks)
        [future.add_done_callback(self.done_queue.put_nowait) for future in futures]
        return futures

    async def close(self) -> None:
        """Close all workers, cancel all futures that have not done"""
        await self.pool.shutdown(
            timeout=0, cancel_queue=True, cancel_tasks=self.cancel_tasks
        )
        while not self.done_queue.empty():
            future = await self.done_queue.get()
            if not future.done():
                future.cancel()
        self.closed.set()

    @property
    def remaining_tasks(self) -> int:
        """Remaining tasks"""
        return self.pool.task_queue.qsize()

    @property
    def running_tasks(self) -> int:
        """Number of tasks running"""
        return len([worker for worker in self.pool.workers if worker.is_running])

    @property
    def is_finish(self) -> bool:
        """Whether all workers are idle or all tasks are"""
        return self.pool.is_finish

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def iter(self) -> typing.AsyncGenerator[asyncio.Future, None]:
        """Run all tasks and yield the result"""
        while True:
            if self.closed.is_set():
                break
            try:
                future = await self.done_queue.get()
                yield future
            except asyncio.CancelledError:
                break
            else:
                self.done_queue.task_done()
