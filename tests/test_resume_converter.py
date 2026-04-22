import pytest

from utils.resume_converter import (
    ConversionFailedError,
    EmptyConversionResultError,
    NoResumeFileFoundError,
    OutputConversionFailedError,
    ResumeConverterError,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    UnsupportedOutputFormatError,
)


class TestExceptionHierarchy:
    def test_all_subclasses_inherit_from_base(self, subtests):
        subclasses = [
            ResumeFileNotFoundError,
            UnsupportedFormatError,
            ConversionFailedError,
            EmptyConversionResultError,
            NoResumeFileFoundError,
            OutputConversionFailedError,
            UnsupportedOutputFormatError,
        ]
        for exc_class in subclasses:
            with subtests.test(msg=exc_class.__name__):
                assert issubclass(exc_class, ResumeConverterError)

    def test_base_is_exception_subclass(self):
        assert issubclass(ResumeConverterError, Exception)

    def test_exceptions_are_raisable_with_message(self, subtests):
        all_classes = [
            ResumeConverterError,
            ResumeFileNotFoundError,
            UnsupportedFormatError,
            ConversionFailedError,
            EmptyConversionResultError,
            NoResumeFileFoundError,
            OutputConversionFailedError,
            UnsupportedOutputFormatError,
        ]
        for exc_class in all_classes:
            with subtests.test(msg=exc_class.__name__):
                with pytest.raises(exc_class, match="test message"):
                    raise exc_class("test message")

    def test_subclass_caught_by_base(self, subtests):
        subclasses = [
            ResumeFileNotFoundError,
            UnsupportedFormatError,
            ConversionFailedError,
            EmptyConversionResultError,
            NoResumeFileFoundError,
            OutputConversionFailedError,
            UnsupportedOutputFormatError,
        ]
        for exc_class in subclasses:
            with subtests.test(msg=exc_class.__name__):
                with pytest.raises(ResumeConverterError):
                    raise exc_class("test")
