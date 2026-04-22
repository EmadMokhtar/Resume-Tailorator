"""Minimal guard test: main() must fail fast until Task 6 wires the memory service."""

import pytest

import main as main_module


@pytest.mark.asyncio
async def test_main_raises_not_implemented_before_task6() -> None:
    """main() must raise NotImplementedError with a Task 6 message rather than passing
    a raw string into workflow.run(), which now expects a structured CV object."""
    with pytest.raises(NotImplementedError, match="Task 6"):
        await main_module.main()
