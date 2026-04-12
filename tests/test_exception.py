from webcompy.exception import WebComPyException


def test_exception_is_exception():
    assert issubclass(WebComPyException, Exception)


def test_exception_message():
    exc = WebComPyException("test error")
    assert str(exc) == "test error"


def test_exception_can_be_raised_and_caught():
    try:
        raise WebComPyException("raised")
    except WebComPyException as e:
        assert str(e) == "raised"
