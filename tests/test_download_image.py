import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import run

class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
    def iter_content(self, chunk_size):
        yield b"data"


def test_download_image_retries(monkeypatch, tmp_path):
    calls = {"count": 0}
    def fake_get(url, stream=True):
        calls["count"] += 1
        return FakeResponse(404 if calls["count"] == 1 else 200)
    monkeypatch.setattr(run.requests, "get", fake_get)
    output = tmp_path / "out.png"
    run.download_image("http://example.com/image.png", output, retries=2, delay=0)
    assert output.read_bytes() == b"data"
    assert calls["count"] == 2
