import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from run import order_check


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeAPI:
    def __init__(self, data):
        self._data = data

    def get(self, endpoint):
        assert endpoint == 'orders'
        return FakeResponse(self._data)


def test_order_check_raises_on_invalid_response():
    api = FakeAPI({'code': 'error', 'message': 'invalid'})
    with pytest.raises(ValueError):
        order_check(api, {}, '', '')
