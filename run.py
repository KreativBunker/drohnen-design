import base64
import io
import json
import os
import time
import sqlite3
import traceback

from ftplib import FTP_TLS
from shutil import copy, copy2

import fitz
import pycountry
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from woocommerce import API


def find_folder_in_subdirectories(root_path: str, target_folder_name: str) -> bool:
    for dirpath, dirnames, _ in os.walk(root_path):
        if target_folder_name in dirnames:
            return True
    return False


def find_folder_path_in_subdirectories(root_path: str, target_folder_name: str) -> str:
    for dirpath, dirnames, _ in os.walk(root_path):
        if target_folder_name in dirnames:
            return os.path.join(dirpath, target_folder_name)
    return None
        
        
def get_skin_file_paths(order_path: str, order_items: list) -> list[str]:
    skin_file_paths = []
    
    item_folders = [i for i in os.listdir(order_path) if i != '.DS_Store']
    for item_folder, item_order in zip(item_folders, order_items):
        _, _, item_product, _, item_quanity = item_folder.split()
        if item_product.endswith(str(item_order['product_id'])) and item_quanity.startswith(str(item_order['quantity'])):
            skin_file_path = order_path + '/' + item_folder + '/stage-1.png'
            if os.path.exists(skin_file_path):
                skin_file_paths.append(skin_file_path)
                
    return skin_file_paths


def get_country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else ''


def get_order_status(id: int):
    order = get_order(id)
    if order:
        return order['status']
    return False


def add_label_to_image(input_file: str, output_file: str, order: dict, label_settings: dict):
    image = Image.open(input_file)

    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    new_width = image.width + (168 * 3)
    new_image = Image.new("RGBA", (new_width, image.height), (255, 255, 255, 0))

    new_image.paste(image, ((168 * 3), 0))

    label_image = Image.new("RGBA", (new_width, image.height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(label_image)

    font_path = label_settings['text_font_path']
    font_bold_path = label_settings['text_bold_font_path']
    font_size = int(label_settings['text_font_size']) * 3

    font_normal = ImageFont.truetype(font_path, font_size)
    font_bold = ImageFont.truetype(font_bold_path, font_size)

    country = get_country_name(order['shipping']['country'])
    
    sender_position = tuple(map(int, label_settings['text_sender_pos'].split(',')))
    receiver_position = tuple(map(int, label_settings['text_receiver_pos'].split(',')))
    
    text_color = (0, 0, 0)
    
    draw.text((sender_position[0] * 3, sender_position[1] + (0 * 3)), "Absender:", font=font_bold, fill=text_color)
    draw.text((sender_position[0] * 3, sender_position[1] + (20 * 3)), label_settings['sender_name'], font=font_normal, fill=text_color)
    draw.text((sender_position[0] * 3, sender_position[1] + (40 * 3)), label_settings['sender_street'], font=font_normal, fill=text_color)
    draw.text((sender_position[0] * 3, sender_position[1] + (60 * 3)), f"{label_settings['sender_postalcode']} {label_settings['sender_city']}", font=font_normal, fill=text_color)
    draw.text((sender_position[0] * 3, sender_position[1] + (80 * 3)), label_settings['sender_country'], font=font_normal, fill=text_color)
    
    draw.text((receiver_position[0] * 3, receiver_position[1] + (0 * 3)), "Empfänger:", font=font_bold, fill=text_color)
    draw.text((receiver_position[0] * 3, receiver_position[1] + (20 * 3)), f"{order['shipping']['first_name']} {order['shipping']['last_name']}", font=font_normal, fill=text_color)
    draw.text((receiver_position[0] * 3, receiver_position[1] + (40 * 3)), order['shipping']['address_1'], font=font_normal, fill=text_color)
    draw.text((receiver_position[0] * 3, receiver_position[1] + (60 * 3)), f"{order['shipping']['postcode']} {order['shipping']['city']}", font=font_normal, fill=text_color)
    draw.text((receiver_position[0] * 3, receiver_position[1] + (80 * 3)), country, font=font_normal, fill=text_color)

    new_image.paste(label_image, (0, 0), label_image)

    new_image.save(output_file, format='PNG', compress_level=0)


def order_check(woocommerce_api: str, label_settings: str, ftp_server: str, ftp_username: str, ftp_password: str) -> None:
    for order in woocommerce_api.get('orders').json():
        if get_order_status(order['id']) == False:
            error_attemps = 0
            while True:
                try:
                    for order_item in order['line_items']:
                        if not order_item['meta_data']:
                            continue
                        
                        for meta in order_item['meta_data']:
                            if 'file' in meta['value']:
                                temp_file_path = meta['value']['file']
                                download_temp_file(ftp_server, ftp_username, ftp_password, temp_file_path)
                                order_item['file_path'] = 'print_file.png'

                    start_printing(order, label_settings)
                    print(f'Order({order["id"]}) completed')

                    break

                except Exception as error:
                    print(f'Order({order["id"]}) failed to print, try again... ({traceback.format_exc()})')
                    error_attemps += 1
                    time.sleep(5)
                
                if error_attemps >= 3:
                    save_order(order['id'], False)
                    print(f'Order({order["id"]}) failed to print')
                    break
                
                
def create_pdf_with_png_and_pdf(png_path, pdf_path, output_pdf_path):
    cut_size = get_pdf_size('cuts/cut.pdf')

    doc = fitz.open()
    page = doc.new_page(width=cut_size[0] + (168 * 3), height=cut_size[1])

    img = Image.open(png_path)

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG", compress_level=0)
    img_buffer.seek(0)

    page.insert_image(page.rect, stream=img_buffer.getvalue())

    overlay_pdf = fitz.open(pdf_path)
    page.show_pdf_page(page.rect, overlay_pdf, 0)

    doc.save(output_pdf_path)
    

def start_printing(order: dict, label_settings: dict) -> None:
    for item in order['line_items']:
        if 'file_path' not in item:
            continue
            raise Exception('File Path missed')
        add_label_to_image(item['file_path'], item['file_path'].replace('stage-1.png', 'skin.png'), order, label_settings)
        create_pdf_with_png_and_pdf(item['file_path'].replace('stage-1.png', 'skin.png'), 'cuts/cut.pdf', item['file_path'].replace('stage-1.png', 'skin.pdf'))
        copy2(item['file_path'].replace('stage-1.png', 'skin.pdf'), f'./test/skin_{item["id"]}.pdf')
        os.remove(item['file_path'])
    save_order(order['id'], True)


def save_base64_to_png(base64_data, output_file):
    try:
        if base64_data.startswith("data:image/"):
            base64_data = base64_data.split(",")[1]
        
        image_data = base64.b64decode(base64_data)
        with open(output_file, "wb") as file:
            file.write(image_data)
    except Exception as e:
        print(f"Fehler beim Speichern von {output_file}: {e}")


def search_keys_in_dict(data, keys, output_dir="."):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                output_file = os.path.join(output_dir, f"{key}.png")
                save_base64_to_png(value, output_file)
            else:
                search_keys_in_dict(value, keys, output_dir)
    elif isinstance(data, list):
        for item in data:
            search_keys_in_dict(item, keys, output_dir)
            

def download_file_from_ftp_tls(server, username, password, remote_file_path, local_file_path):

    with FTP_TLS(server) as ftp:
        ftp.login(user=username, passwd=password)
        ftp.prot_p()
        
        with open(local_file_path, 'wb') as local_file:
            ftp.retrbinary(f"RETR {remote_file_path}", local_file.write)



def download_temp_file(ftp_server: str, ftp_username: str, ftp_password: str, file_path: str):
    file_path = file_path + '.tmp'
    temp_output_file = file_path.split('/')[len(file_path.split('/'))-1]
    temp_output_json_file = temp_output_file.replace('.tmp', '.json')


    download_file_from_ftp_tls(
        server=ftp_server,
        username=ftp_username,
        password=ftp_password,
        remote_file_path=f"/wp-content/uploads/lumise_data/user_data/{file_path}",
        local_file_path=temp_output_file
    )

    try:
        if os.path.exists(temp_output_file):
            copy(temp_output_file, temp_output_json_file)
        else:
            exit()

        with open(temp_output_json_file, "r") as file:
            data = json.load(file)

        keys = ["print_file"]

        search_keys_in_dict(data, keys)

        os.remove(temp_output_file)
        os.remove(temp_output_json_file)

    except Exception as e:
        print(f"Fehler beim Verarbeiten der Datei: {e}")


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


def save_order(id: int, status: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (id, status) VALUES (?, ?)", (id, status))
    conn.commit()
    conn.close()


def get_orders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, created_at FROM orders")
    orders = cursor.fetchall()
    conn.close()
    
    return [{"id": order[0], "status": bool(order[1]), "created_at": order[2]} for order in orders]


def get_order(id: int):
    orders = get_orders()
    
    if orders:
        for order in orders:
            if order['id'] == id:
                return order
        
    return None


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

    FTP_SERVER = os.getenv('FTP_SERVER')
    FTP_USERNAME = os.getenv('FTP_USERNAME')
    FTP_PASSWORD = os.getenv('FTP_PASSWORD')
    
    while True:
        try:
            order_check(
                WOOCOMMERCE_API,
                LABEL_SETTINGS,
                FTP_SERVER,
                FTP_USERNAME,
                FTP_PASSWORD
            )

        except Exception as error:
            print(error)

        time.sleep(5)