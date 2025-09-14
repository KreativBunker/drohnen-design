import base64
import io
import os
import time
import sqlite3
import requests
import traceback

import fitz
import pycountry
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from woocommerce import API


def get_country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else ''


def get_order_status(order: dict):
    order = get_order(order)
    if order:
        return order['status']
    return False


def add_label_to_pdf(input_file: str, output_file: str, order: dict, label_settings: dict):
    doc = fitz.open(input_file)
    out_doc = fitz.open()

    def load_font(path: str | None, fallback: str) -> ImageFont.FreeTypeFont:
        """Resolve and load the given font.

        If ``path`` is not provided or the file cannot be loaded, a fallback
        font bundled with the repository is used. ``fallback`` should be the
        path to that bundled font relative to this file.
        """

        if not path:
            path = fallback
        if not os.path.isabs(path):
            candidate = os.path.join(os.path.dirname(__file__), path)
            if os.path.exists(candidate):
                path = candidate
        try:
            return ImageFont.truetype(path, font_size)
        except OSError:
            fallback_path = os.path.join(os.path.dirname(__file__), fallback)
            return ImageFont.truetype(fallback_path, font_size)

    font_size = int(label_settings['text_font_size']) * 3

    font_normal = load_font(label_settings.get('text_font_path'), os.path.join('fonts', 'roboto.ttf'))
    font_bold = load_font(label_settings.get('text_bold_font_path'), os.path.join('fonts', 'Roboto-Bold.ttf'))

    country = get_country_name(order['shipping']['country'])
    
    sender_position = tuple(map(int, label_settings['text_sender_pos'].split(',')))
    receiver_position = tuple(map(int, label_settings['text_receiver_pos'].split(',')))
    
    text_color = (0, 0, 0)
    dpi = 150
    
    scale = dpi / 72  # convert between PDF points (72 DPI) and target resolution
    extra_width_pt = 178  # desired label margin in PDF points
    extra_width_px = int(extra_width_pt * scale)

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)

        old_width_px, old_height_px = pix.width, pix.height
        old_width_pt, old_height_pt = page.rect.width, page.rect.height
        new_width_px = old_width_px + extra_width_px
        new_width_pt = old_width_pt + extra_width_pt

        image = Image.new("RGB", (new_width_px, old_height_px), (255, 255, 255))
        page_image = Image.frombytes("RGB", [old_width_px, old_height_px], pix.samples)

        image.paste(page_image, (extra_width_px, 0))

        draw = ImageDraw.Draw(image)

        draw.text((70, sender_position[1]), "Absender:", font=font_bold, fill=text_color)
        draw.text((70, sender_position[1] + 30), label_settings['sender_name'], font=font_normal, fill=text_color)
        draw.text((70, sender_position[1] + 60), label_settings['sender_street'], font=font_normal, fill=text_color)
        draw.text((70, sender_position[1] + 90), f"{label_settings['sender_postalcode']} {label_settings['sender_city']}", font=font_normal, fill=text_color)
        draw.text((70, sender_position[1] + 120), label_settings['sender_country'], font=font_normal, fill=text_color)

        draw.text((70, receiver_position[1]), "Empfänger:", font=font_bold, fill=text_color)
        draw.text((70, receiver_position[1] + 30), f"{order['shipping']['first_name']} {order['shipping']['last_name']}", font=font_normal, fill=text_color)
        draw.text((70, receiver_position[1] + 60), order['shipping']['address_1'], font=font_normal, fill=text_color)
        draw.text((70, receiver_position[1] + 90), f"{order['shipping']['postcode']} {order['shipping']['city']}", font=font_normal, fill=text_color)
        draw.text((70, receiver_position[1] + 120), country, font=font_normal, fill=text_color)

        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG", optimize=True)
        img_buffer.seek(0)

        new_page = out_doc.new_page(width=new_width_pt, height=old_height_pt)
        new_page.insert_image(
            fitz.Rect(0, 0, new_width_pt, old_height_pt), stream=img_buffer.getvalue()
        )

    out_doc.save(output_file)
    out_doc.close()
    doc.close()


def merge_cut_file(base_pdf_path: str, overlay_pdf_path: str, output_pdf_path: str):
    base_pdf = fitz.open(base_pdf_path)
    overlay_pdf = fitz.open(overlay_pdf_path)

    min_pages = min(len(base_pdf), len(overlay_pdf))

    for i in range(min_pages):
        base_page = base_pdf[i]
        overlay_page = overlay_pdf[i]

        # Center overlay page on the base page
        x_offset = (base_page.rect.width - overlay_page.rect.width) / 2
        y_offset = (base_page.rect.height - overlay_page.rect.height) / 2

        rect = fitz.Rect(
            x_offset,
            y_offset,
            x_offset + overlay_page.rect.width,
            y_offset + overlay_page.rect.height,
        )
        base_page.show_pdf_page(rect, overlay_pdf, i)

    base_pdf.save(output_pdf_path)
    base_pdf.close()
    overlay_pdf.close()

def find_key_in_nested_dict(data, key):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for k, v in data.items():
            result = find_key_in_nested_dict(v, key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_key_in_nested_dict(item, key)
            if result is not None:
                return result
    return None

def get_print_id(order_item: dict):
    for meta in WOOCOMMERCE_API.get(f"products/{order_item['product_id']}").json()['meta_data']:
        if meta['key'] == 'druck-id':
            return meta['value']
    return None


def get_cut_file(order_item: dict):
    print_id = get_print_id(order_item)
    for file in os.listdir('cuts'):
        if print_id == file:
            return f'cuts/{file}'
    return None


def get_print_dpi(order_item: dict, default: int = 150) -> int:
    product = WOOCOMMERCE_API.get(f"products/{order_item['product_id']}").json()
    for meta in product.get('meta_data', []):
        if meta['key'] == '_dvpd_dpi':
            try:
                return int(meta['value'])
            except (TypeError, ValueError):
                break
    return default


def download_image(url: str, output_file: str, retries: int = 5, delay: float = 2.0):
    last_status = None
    for _ in range(retries):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_file, "wb") as image_file:
                for chunk in response.iter_content(1024):
                    image_file.write(chunk)
            return
        last_status = response.status_code
        time.sleep(delay)
    raise Exception(f"Failed to download image: {url}, status code {last_status}")


def png_to_pdf(png_path: str, pdf_path: str, dpi: int = 150):
    image = Image.open(png_path)
    rgb_image = image.convert('RGB')
    rgb_image.save(pdf_path, resolution=dpi)


def start_printing(order: dict, order_item: dict, pdf_path: str, label_settings: dict, hotfolder_path: str) -> None:
    file_output_path = f"temp/label_{order['id']}_{order_item['id']}.pdf"
    add_label_to_pdf(pdf_path, file_output_path, order, label_settings)
    cut_file = get_cut_file(order_item)

    if not cut_file:
        raise Exception('Cut file not found')

    final_output = f"{hotfolder_path}/final_{order['id']}_{order_item['id']}.pdf"
    merge_cut_file(file_output_path, cut_file, final_output)

    os.remove(pdf_path)
    os.remove(file_output_path)


def save_base64_to_png(base64_data, output_file):
    try:
        if base64_data.startswith("data:image/"):
            base64_data = base64_data.split(",")[1]
        
        image_data = base64.b64decode(base64_data)
        with open(output_file, "wb") as file:
            file.write(image_data)
    except Exception as e:
        print(f"Fehler beim Speichern von {output_file}: {e}")


def create_db(db_name: str):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            status BOOLEAN NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_order(order: dict, status: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (id, status) VALUES (?, ?)", (order['id'], status))
    conn.commit()
    conn.close()
    
    
def update_order(order: dict, status: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order['id']))
    conn.commit()
    conn.close()


def get_orders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, created_at FROM orders")
    orders = cursor.fetchall()
    conn.close()
    
    return [{"id": order[0], "status": bool(order[1]), "created_at": order[2]} for order in orders]


def get_order(order: dict):
    orders_db = get_orders()
    if orders_db:
        for order_db in orders_db:
            if order_db['id'] == order['id']:
                return order_db
    return None


def order_check(woocommerce_api: API, label_settings: dict, hotfolder_path: str, url: str) -> None:
    attempts = 3
    orders_response = None
    for _ in range(attempts):
        orders_response = woocommerce_api.get('orders').json()
        if isinstance(orders_response, list):
            break
        print(
            f"Unexpected response from WooCommerce API: {orders_response},"
            " retrying...",
        )
        time.sleep(5)
    else:
        raise ValueError(f"Unexpected response from WooCommerce API: {orders_response}")
    for order in orders_response:
        # Skip orders that have not been paid yet
        if order.get('status') not in {"processing", "completed"}:
            continue
        if get_order_status(order) == False:
            error_attemps = 0
            while True:
                try:
                    for item in order['line_items']:
                        png_url = f"{url}/Order/order-{order['id']}/item-{item['id']}.png"
                        png_path = f"temp/{order['id']}_{item['id']}.png"
                        pdf_path = f"temp/{order['id']}_{item['id']}.pdf"
                        download_image(png_url, png_path)
                        dpi = get_print_dpi(item)
                        png_to_pdf(png_path, pdf_path, dpi)
                        start_printing(order, item, pdf_path, label_settings, hotfolder_path)
                        os.remove(png_path)
                    if get_order(order):
                        update_order(order, True)
                    else:
                        save_order(order, True)
                    print(f'Order({order["id"]}) completed')
                    break
                except Exception as error:
                    print(f'Order({order["id"]}) failed to print, try again... ({traceback.format_exc()})')
                    error_attemps += 1
                    time.sleep(5)

                if error_attemps >= 3:
                    if not get_order(order):
                        save_order(order, -1)
                    else:
                        update_order(order, -1)
                    print(f'Order({order["id"]}) failed to print')
                    break


if __name__ == '__main__':
    load_dotenv(override=True)
    
    DB_NAME = os.getenv('DB_NAME')
    create_db(DB_NAME)
    
    URL = os.getenv('URL')
    CONSUMER_KEY = os.getenv('CONSUMER_KEY')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
    
    SENDER_NAME = os.getenv('SENDER_NAME')
    SENDER_STREET = os.getenv('SENDER_STREET')
    SENDER_POSTALCODE = os.getenv('SENDER_POSTALCODE')
    SENDER_CITY = os.getenv('SENDER_CITY')
    SENDER_COUNTRY = os.getenv('SENDER_COUNTRY')
    
    TEXT_FONT_PATH = os.getenv('TEXT_FONT_PATH')
    TEXT_BOLD_FONT_PATH = os.getenv('TEXT_BOLD_FONT_PATH')
    TEXT_FONT_SIZE = os.getenv('TEXT_FONT_SIZE')
    TEXT_SENDER_POS = os.getenv('TEXT_SENDER_POS')
    TEXT_RECEIVER_POS = os.getenv('TEXT_RECEIVER_POS')
    
    LABEL_SETTINGS = {
        'text_font_path': TEXT_FONT_PATH,
        'text_bold_font_path': TEXT_BOLD_FONT_PATH,
        'text_font_size': TEXT_FONT_SIZE,
        'text_sender_pos': TEXT_SENDER_POS,
        'text_receiver_pos': TEXT_RECEIVER_POS,
        'sender_name': SENDER_NAME,
        'sender_street': SENDER_STREET,
        'sender_postalcode': SENDER_POSTALCODE,
        'sender_city': SENDER_CITY,
        'sender_country': SENDER_COUNTRY
    }

    WOOCOMMERCE_API = API(
        url=URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version='wc/v3'
    )
    
    HOTFOLDER_PATH = os.getenv('HOTFOLDER_PATH')
    
    while True:
        try:
            order_check(
                WOOCOMMERCE_API,
                LABEL_SETTINGS,
                HOTFOLDER_PATH,
                URL
            )
        except Exception as error:
            print(error)

        time.sleep(5)
