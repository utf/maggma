import pytest
import time
import asyncio
from maggma.cli.multiprocessing import (
    grouper,
    BackPressure,
    AsyncUnorderedMap,
    safe_dispatch,
)
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.asyncio
async def test_grouper():
    async def arange(count):
        for i in range(count):
            yield (i)

    async for group in grouper(arange(100), n=10):
        assert len(group) == 10

    async for group in grouper(arange(9), n=10):
        assert len(group) == 9


def wait_and_return(x):
    time.sleep(1)
    return x * x


async def arange(n):
    for num in range(n):
        yield num


@pytest.mark.asyncio
async def test_backpressure():

    iterable = range(10)
    backpressure = BackPressure(iterable, 2)

    # Put two items into the process queue
    asyncio.gather(backpressure.__anext__(), backpressure.__anext__())

    # Ensure back_pressure enabled
    assert backpressure.back_pressure.locked()

    releaser = backpressure.release(arange(10))
    await releaser.__anext__()
    assert not backpressure.back_pressure.locked()
    asyncio.gather(releaser.__anext__(), releaser.__anext__())
    assert not backpressure.back_pressure.locked()


@pytest.mark.asyncio
async def test_async_map():

    executor = ThreadPoolExecutor(1)
    amap = AsyncUnorderedMap(wait_and_return, arange(3), executor)
    true_values = {x * x for x in range(3)}

    finished_vals = set()
    async for finished_val in amap:
        finished_vals.add(finished_val)

    assert finished_vals == true_values


def test_safe_dispatch():
    def bad_func(val):
        raise ValueError("AAAH")

    safe_dispatch((bad_func, ""))
