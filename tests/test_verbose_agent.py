"""Tests for run_agent() verbose streaming helper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import Agent

from resume_tailorator.workflows.agents import run_agent


class _AsyncIter:
    """Minimal async iterator for mocking stream_text() output."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


class TestRunAgentNonVerbose:
    """When verbose=False, run_agent delegates directly to agent.run()."""

    @pytest.mark.asyncio
    async def test_delegates_to_agent_run(self):
        agent = MagicMock(spec=Agent)
        expected = MagicMock()
        agent.run = AsyncMock(return_value=expected)

        result = await run_agent(agent, "test prompt", verbose=False)

        agent.run.assert_awaited_once()
        assert result is expected

    @pytest.mark.asyncio
    async def test_passes_usage_params(self):
        agent = MagicMock(spec=Agent)
        agent.run = AsyncMock()

        await run_agent(agent, "test", verbose=False, usage="u", usage_limits="ul")

        agent.run.assert_awaited_once_with("test", usage="u", usage_limits="ul")


class TestRunAgentVerbose:
    """When verbose=True, run_agent uses run_stream_events and prints to console."""

    @pytest.mark.asyncio
    async def test_prints_steam_header(self):
        agent = MagicMock(spec=Agent)
        agent.run = AsyncMock()
        agent.run_stream_events = MagicMock()

        # Return an empty async iterator (no streaming events)
        agent.run_stream_events.return_value.__aenter__ = AsyncMock(
            return_value=_AsyncIter([])
        )

        with patch("resume_tailorator.workflows.agents._console") as mock_console:
            result = await run_agent(
                agent, "test prompt", verbose=True, agent_label="TestAgent"
            )

        assert mock_console.print.assert_any_call
        # run_stream_events was called with correct prompt/kwargs
        agent.run_stream_events.assert_called_once_with(
            "test prompt", usage=None, usage_limits=None
        )

    @pytest.mark.asyncio
    async def test_falls_back_on_stream_error(self):
        agent = MagicMock(spec=Agent)
        fallback_result = MagicMock()
        agent.run = AsyncMock(return_value=fallback_result)

        # Make run_stream_events return an object that raises on async iteration
        bad_iter = MagicMock()
        bad_iter.__aiter__ = MagicMock(side_effect=RuntimeError("stream boom"))
        agent.run_stream_events = MagicMock(return_value=bad_iter)

        with patch("resume_tailorator.workflows.agents._console"):
            with patch("resume_tailorator.workflows.agents.logger") as mock_logger:
                result = await run_agent(
                    agent, "test", verbose=True, agent_label="Test"
                )

        mock_logger.warning.assert_called_once()
        agent.run.assert_awaited_once()
        assert result is fallback_result
