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

    font_path = label_settings['text_font_path']
    font_bold_path = label_settings['text_bold_font_path']
    font_size = int(label_settings['text_font_size']) * 3

    font_normal = ImageFont.truetype(font_path, font_size)
    font_bold = ImageFont.truetype(font_bold_path, font_size)

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

        draw.text((20, sender_position[1]), "Absender:", font=font_bold, fill=text_color)
        draw.text((20, sender_position[1] + 20), label_settings['sender_name'], font=font_normal, fill=text_color)
        draw.text((20, sender_position[1] + 40), label_settings['sender_street'], font=font_normal, fill=text_color)
        draw.text((20, sender_position[1] + 60), f"{label_settings['sender_postalcode']} {label_settings['sender_city']}", font=font_normal, fill=text_color)
        draw.text((20, sender_position[1] + 80), label_settings['sender_country'], font=font_normal, fill=text_color)

        draw.text((20, receiver_position[1]), "Empfänger:", font=font_bold, fill=text_color)
        draw.text((20, receiver_position[1] + 20), f"{order['shipping']['first_name']} {order['shipping']['last_name']}", font=font_normal, fill=text_color)
        draw.text((20, receiver_position[1] + 40), order['shipping']['address_1'], font=font_normal, fill=text_color)
        draw.text((20, receiver_position[1] + 60), f"{order['shipping']['postcode']} {order['shipping']['city']}", font=font_normal, fill=text_color)
        draw.text((20, receiver_position[1] + 80), country, font=font_normal, fill=text_color)

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
        base_page.show_pdf_page(base_page.rect, overlay_pdf, i)

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

def get_print_id(order: dict):
    for order_item in order['line_items']:
        for meta in WOOCOMMERCE_API.get(f"products/{order_item['product_id']}").json()['meta_data']:
            if meta['key'] == 'druck-id':
                return meta['value']
    return None


def get_file_id(order: dict):
    for order_item in order['line_items']:
        if not order_item['meta_data']:
            continue
        for meta in order_item['meta_data']:
            if 'file' in meta['value']:
                file_id = str(meta['value']['file']).split('_')[0].split('/')[2]
                return file_id
    return None
    

def get_cut_file(order: dict):
    print_id = get_print_id(order)
    for file in os.listdir('cuts'):
        if print_id == file:
            return f'cuts/{file}'
    return None


def start_printing(order: dict, label_settings: dict, hotfolder_path: str) -> None:
    file_id = get_file_id(order)
    for file in os.listdir('temp'):
        if f'{file_id}.pdf' == file:
            file_path = f'temp/{file}'
            file_output_path = f'temp/label_{file}'
            add_label_to_pdf(file_path, file_output_path, order, label_settings)
            cut_file = get_cut_file(order)
            
            if not cut_file:
                raise Exception('Cut file not found')
            
            final_output = f'{hotfolder_path}/final_{file}'
            merge_cut_file(file_output_path, cut_file, final_output)
            
            if get_order(order):
                update_order(order, True)
            else:
                save_order(order, True)
                
            os.remove(file_path)
            os.remove(file_output_path)
                
            break


def save_base64_to_png(base64_data, output_file):
    try:
        if base64_data.startswith("data:image/"):
            base64_data = base64_data.split(",")[1]
        
        image_data = base64.b64decode(base64_data)
        with open(output_file, "wb") as file:
            file.write(image_data)
    except Exception as e:
        print(f"Fehler beim Speichern von {output_file}: {e}")
            

def download_pdf(url: str, output_file: str):
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with open(output_file, "wb") as pdf_file:
            for chunk in response.iter_content(1024):
                pdf_file.write(chunk)


def get_pdf_size(file_path: str) -> list:
    pdf_document = fitz.open(file_path)
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        width = int(page.rect.width)
        height = int(page.rect.height)
    return [width, height]


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


def order_check(woocommerce_api: str, label_settings: str, hotfolder_path: str, url: str) -> None:
    for order in woocommerce_api.get('orders').json():
        if get_order_status(order) == False:
            error_attemps = 0
            while True:
                try:
                    file_id = get_file_id(order)
                    download_pdf(f'{url}/design-editor/?pdf_download={file_id}', f'temp/{file_id}.pdf')
                    start_printing(order, label_settings, hotfolder_path)
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
