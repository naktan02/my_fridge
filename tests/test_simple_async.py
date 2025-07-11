import asyncio
import pytest

# anyio가 제대로 동작하는지 확인하기 위한 가장 간단한 테스트
async def test_simple_sleep():
    await asyncio.sleep(0.01)
    assert True