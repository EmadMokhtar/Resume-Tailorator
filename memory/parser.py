"""Parser adapter for the resume memory subsystem.

Wraps the existing resume_parser_agent behind a narrow interface so that the
service layer is decoupled from pydantic-ai internals and can be tested with a
simple fake.

Only the abstract base class and the concrete pydantic-ai adapter live here;
callers that need to inject a fake should subclass ``ResumeParserAdapter``.

``workflows.agents`` is imported lazily inside ``PydanticAIResumeParser.parse``
to avoid requiring an ``OPENAI_API_KEY`` at import time (tests use a fake).
"""

from abc import ABC, abstractmethod

from models.agents.output import CV

_PARSER_VERSION = "1.0.0"


class ResumeParserAdapter(ABC):
    """Narrow interface for resume parsing used by ``ResumeMemoryService``."""

    @property
    @abstractmethod
    def parser_version(self) -> str:
        """Version string for this parser.

        Bump this whenever the prompt or output schema changes so that the
        service can detect stale cached parses and trigger a re-parse.

        Declaring this as an abstract property (rather than a bare class-level
        annotation) ensures that any concrete subclass that forgets to
        implement it will fail loudly at instantiation time with a
        ``TypeError``, rather than silently producing a runtime
        ``AttributeError`` later.
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, content: str) -> CV:
        """Parse raw resume text and return a structured ``CV``.

        Args:
            content: Raw markdown (or plain-text) resume content.

        Returns:
            A fully populated ``CV`` model instance.
        """
        raise NotImplementedError


class PydanticAIResumeParser(ResumeParserAdapter):
    """Concrete adapter that delegates to the pydantic-ai ``resume_parser_agent``.

    ``workflows.agents`` is imported lazily so that importing this module does
    not require a live ``OPENAI_API_KEY`` (useful in test and CI environments
    that use fake/stub parsers instead).
    """

    @property
    def parser_version(self) -> str:
        """Return the current parser version string."""
        return _PARSER_VERSION

    def parse(self, content: str) -> CV:
        """Synchronously parse *content* using the resume parser agent.

        Args:
            content: Raw resume text (markdown or plain text).

        Returns:
            Structured ``CV`` instance produced by the agent.

        Raises:
            ValueError: If the agent returns no structured output.
            TypeError: If the agent returns a payload that is not a ``CV``.
        """
        # Lazy import to avoid OpenAI client instantiation at module load time.
        from workflows.agents import resume_parser_agent  # noqa: PLC0415

        result = resume_parser_agent.run_sync(content)
        output = result.output

        if output is None:
            raise ValueError(
                "Resume parser agent returned no output; expected a CV instance."
            )

        if not isinstance(output, CV):
            raise TypeError(
                "Resume parser agent returned invalid output type "
                f"{type(output).__name__}; expected CV."
            )

        return output
