import asyncio
import concurrent.futures
import logging
import random
import threading
import time
import typing
import unittest

import pytest

from secretscraper.coroutinue import (
    AsyncPool,
    AsyncPoolCollector,
    AsyncTask,
    AsyncWorker,
)

logger = logging.getLogger(__name__)


async def async_increment(i: int, sec: float) -> int:
    await asyncio.sleep(sec)
    return i + 1


@pytest.fixture(scope="class")
def task_queue_half_sec():
    queue = asyncio.Queue()
    task = AsyncTask(async_increment, 1, 0.5)
    [queue.put_nowait(task) for _ in range(5)]
    return queue


def generate_task(
    num: int, sec: float = 0.5
) -> typing.Generator[list[AsyncTask], None, None]:
    yield [AsyncTask(async_increment, i, sec) for i in range(num)]


class TestCoroutineAsyncWorker:
    @pytest.mark.asyncio
    async def test_coroutine_async_task(self):
        gen = generate_task(1)
        task = next(gen)[0]
        start = time.perf_counter()
        a_task = asyncio.create_task(task.func(*task.args, **task.kwargs))
        ret = await a_task
        end = time.perf_counter()
        logger.info(f"Task finish in {end - start} seconds")
        logger.info(f"Task return: {ret}")

        task.future.set_result(ret)
        assert task.future.done() is True
        assert task.future.result() == ret

    @pytest.mark.asyncio
    async def test_coroutine_async_worker_normal_finish(
        self, task_queue_half_sec, event_loop
    ):
        queue = asyncio.Queue()
        task = next(generate_task(1, sec=0.5))[0]
        queue.put_nowait(task)
        worker = AsyncWorker(queue, event_loop)
        worker.start()
        try:
            await worker.stop(timeout=0.6)
        except asyncio.TimeoutError as err:
            pass
        assert worker.is_running is False
        assert task.future.done() is True
        assert task.future.result() == 1
        assert task.future.exception() is None

    @pytest.mark.asyncio
    async def test_coroutine_async_worker_abnormal_finish(
        self, task_queue_half_sec, event_loop
    ):
        queue = asyncio.Queue()
        task = next(generate_task(1, sec=0.5))[0]
        queue.put_nowait(task)
        worker = AsyncWorker(queue, event_loop)
        worker.start()
        try:
            await worker.stop(timeout=0)
        except asyncio.TimeoutError as err:
            pass
        assert worker.is_running is False
        assert task.future.done() is False
        with pytest.raises(asyncio.InvalidStateError):
            task.future.result()
        with pytest.raises(asyncio.InvalidStateError):
            task.future.exception()


class TestCoroutineAsyncPool:
    # @pytest.fixture(autouse=True)
    # def get_pool(self):
    #     self.pool = AsyncPool(num_workers=100, event_loop=asyncio.new_event_loop(), queue_capacity=1000)

    async def get_pool(self):
        if not hasattr(self, "pool") or getattr(self, "pool", None) is None:
            self.pool = AsyncPool(
                num_workers=100,
                event_loop=asyncio.get_event_loop(),
                queue_capacity=1000,
            )

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_submit(self):
        """Submit one task"""
        await self.get_pool()
        gen = generate_task(1, 0.5)
        task = next(gen)[0]
        start = time.perf_counter()
        future = await self.pool.submit(task)
        assert self.pool.task_queue.qsize() == 1
        assert self.pool.is_finish is False

        await asyncio.sleep(0.6)
        end = time.perf_counter()
        assert self.pool.is_finish is True
        assert future.done() and future.result() == 1
        assert end - start <= 0.7

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_submit_all(self):
        await self.get_pool()

        gen = generate_task(100, 0.5)
        tasks = next(gen)
        start = time.perf_counter()
        futures = await self.pool.submit_all(tasks)
        assert self.pool.task_queue.qsize() == 100
        assert self.pool.is_finish is False

        await asyncio.sleep(0.6)
        end = time.perf_counter()
        assert self.pool.is_finish is True
        i = 1
        for f in futures:
            assert f.done()
            assert f.result() == i
            i += 1
        assert end - start <= 0.7
        logger.info(f"Task finished in {end - start}")

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_normal_shutdown(self):
        await self.get_pool()

        gen = generate_task(100, 1)
        tasks = next(gen)
        start = time.perf_counter()
        futures = await self.pool.submit_all(tasks)
        assert self.pool.is_finish is False

        await self.pool.shutdown(0.5, cancel_queue=True)
        assert self.pool.is_finish is True
        assert self.pool.task_queue.empty() is True
        end = time.perf_counter()
        assert end - start < 0.6


class TestCoroutineAsyncPoolCollector:

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_collector_submit(self):
        """Submit one task, shutdown automatically"""
        task = next(generate_task(1, 0.5))[0]
        start = time.perf_counter()

        async with AsyncPoolCollector.create_pool(
            100, 1000, asyncio.get_event_loop()
        ) as pool:
            future = await pool.submit(task)
            assert pool.is_finish is False
            assert pool.remaining_tasks == 1
            assert pool.running_tasks == 0

            await asyncio.sleep(0.6)
            assert pool.is_finish is True
            assert pool.remaining_tasks == 0
            assert pool.running_tasks == 0
            end = time.perf_counter()
            assert end - start <= 0.7

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_collector_close(self):
        """Submit multiple task, shutdown manually"""
        tasks = next(generate_task(100, 0.5))
        start = time.perf_counter()

        async with AsyncPoolCollector.create_pool(
            100, 1000, asyncio.get_event_loop()
        ) as pool:
            future = await pool.submit_all(tasks)
            assert pool.is_finish is False
            assert pool.remaining_tasks == 100
            assert pool.running_tasks == 0

        end = time.perf_counter()
        assert end - start <= 0.1

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_collector_submit_all(self):
        """Submit multiple task, shutdown automatically"""
        tasks = next(generate_task(100, 0.5))
        start = time.perf_counter()

        async with AsyncPoolCollector.create_pool(
            100, 1000, asyncio.get_event_loop()
        ) as pool:
            futures = await pool.submit_all(tasks)
            assert pool.is_finish is False
            assert pool.remaining_tasks == 100
            assert pool.running_tasks == 0

            await asyncio.sleep(0.6)
            assert pool.is_finish is True
            assert pool.remaining_tasks == 0
            assert pool.running_tasks == 0
            end = time.perf_counter()
            assert end - start <= 0.7

    @pytest.mark.asyncio
    async def test_coroutine_async_pool_collector_iter(self):
        """Submit multiple task, shutdown automatically"""
        tasks = next(generate_task(100, 0.5))
        start = time.perf_counter()

        async with AsyncPoolCollector.create_pool(
            100, 1000, asyncio.get_event_loop()
        ) as pool:
            futures = await pool.submit_all(tasks)
            assert pool.is_finish is False
            assert pool.remaining_tasks == 100
            assert pool.running_tasks == 0

            num_done_tasks = 0
            result_list = []
            async for future in pool.iter():
                assert future.done() is True
                num_done_tasks += 1
                if num_done_tasks == 100:
                    break
                result_list.append(future.result())

            assert pool.is_finish is True
            assert pool.remaining_tasks == 0
            assert pool.running_tasks == 0
            end = time.perf_counter()
            assert end - start <= 0.7
