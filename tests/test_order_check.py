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


class FakeAPIMulti:
    def __init__(self, responses):
        self._responses = responses
        self.calls = 0

    def get(self, endpoint):
        assert endpoint == 'orders'
        resp = self._responses[self.calls]
        self.calls += 1
        return FakeResponse(resp)


def test_order_check_raises_on_invalid_response(monkeypatch):
    api = FakeAPI({'code': 'error', 'message': 'invalid'})
    monkeypatch.setattr('run.time.sleep', lambda x: None)
    with pytest.raises(ValueError):
        order_check(api, {}, '', '')


def test_order_check_skips_unpaid_orders(monkeypatch):
    orders = [
        {"id": 1, "status": "pending", "line_items": [{"id": 10}]},
        {"id": 2, "status": "processing", "line_items": [{"id": 20}]},
    ]
    api = FakeAPI(orders)

    calls = []
    monkeypatch.setattr('run.get_order_status', lambda order: False)
    monkeypatch.setattr('run.download_image', lambda url, path: None)
    monkeypatch.setattr('run.png_to_pdf', lambda png, pdf, dpi: None)
    monkeypatch.setattr('run.get_print_dpi', lambda item: 150)
    monkeypatch.setattr('run.get_order', lambda o: None)
    monkeypatch.setattr('run.update_order', lambda order, status: None)
    monkeypatch.setattr('run.save_order', lambda order, status: None)
    monkeypatch.setattr('run.os.remove', lambda path: None)

    def fake_start_printing(order, item, pdf_path, label_settings, hotfolder_path):
        calls.append((order['id'], item['id']))

    monkeypatch.setattr('run.start_printing', fake_start_printing)

    order_check(api, {}, '', '')

    assert calls == [(2, 20)]


def test_order_check_retries_and_succeeds(monkeypatch):
    orders_list = [
        {"id": 3, "status": "processing", "line_items": [{"id": 30}]},
    ]
    api = FakeAPIMulti([
        {"code": "internal_server_error"},
        orders_list,
    ])
    monkeypatch.setattr('run.get_order_status', lambda order: False)
    monkeypatch.setattr('run.download_image', lambda url, path: None)
    monkeypatch.setattr('run.png_to_pdf', lambda png, pdf, dpi: None)
    monkeypatch.setattr('run.get_print_dpi', lambda item: 150)
    monkeypatch.setattr('run.get_order', lambda o: None)
    monkeypatch.setattr('run.update_order', lambda order, status: None)
    monkeypatch.setattr('run.save_order', lambda order, status: None)
    monkeypatch.setattr('run.os.remove', lambda path: None)
    monkeypatch.setattr('run.time.sleep', lambda x: None)

    calls = []

    def fake_start_printing(order, item, pdf_path, label_settings, hotfolder_path):
        calls.append((order['id'], item['id']))

    monkeypatch.setattr('run.start_printing', fake_start_printing)

    order_check(api, {}, '', '')

    assert calls == [(3, 30)]
