import pytest
import fitz
from PIL import Image
from run import png_to_pdf


def test_png_to_pdf_respects_dpi(tmp_path):
    img_path = tmp_path / "input.png"
    pdf_path = tmp_path / "output.pdf"
    image = Image.new("RGB", (100, 100), color="red")
    image.save(img_path)
    png_to_pdf(str(img_path), str(pdf_path), dpi=200)
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    assert page.rect.width == pytest.approx((100 / 200) * 72)
    assert page.rect.height == pytest.approx((100 / 200) * 72)
    doc.close()
