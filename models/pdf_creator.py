import fitz
import io


class PDFCreator:
    @staticmethod
    def create_with_overlay(png_path, pdf_path, output_pdf_path):
        doc = fitz.open()
        cut_size = fitz.open(pdf_path)[0].rect
        page = doc.new_page(width=cut_size.width + (168 * 3), height=cut_size.height)

        with open(png_path, "rb") as img_file:
            img_buffer = io.BytesIO(img_file.read())

        page.insert_image(page.rect, stream=img_buffer.getvalue())
        overlay_pdf = fitz.open(pdf_path)
        page.show_pdf_page(page.rect, overlay_pdf, 0)
        doc.save(output_pdf_path)