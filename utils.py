from PIL import Image, ImageDraw, ImageFont
from models import AppConfig

import pycountry
import cairosvg
import fitz
import json
import os
import io


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


def is_order_already_completed(order: dict) -> bool:
    orders_completed = load_json('orders_completed.json')
    
    if not 'data' in orders_completed:
        orders_completed['data'] = []
        
        
    if orders_completed['data']:
        orders_id = [order['id'] for order in orders_completed['data']]
        if order['id'] in orders_id:
            return True
        
    return False
        
        
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


def set_order_completed(order: dict):
    orders_completed = load_json('orders_completed.json')
    if not 'data' in orders_completed:
        orders_completed['data'] = []
    orders_completed['data'].append(order)
    save_json('orders_completed.json', orders_completed)
        
        
def save_json(file_path: str, data: dict) -> None:
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
        
        
def load_json(file_path: str) -> dict:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        return data
    return {}


def get_country_name(code):
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else ''


def add_label_to_image(input_file: str, output_file: str, order: dict, label_settings: dict):
    image = Image.open(input_file)
    
    new_width = image.width + 168
    new_image = Image.new("RGB", (new_width, image.height), (255, 255, 255))
    
    new_image.paste(image, (168, 0))
    
    label_image = Image.new("RGBA", (300, 300), (255, 255, 255, 0))
    draw = ImageDraw.Draw(label_image)

    font_path = "font/roboto.ttf"
    font_size = 8
    font = ImageFont.truetype(font_path, font_size)
    
    country = get_country_name(order['shipping']['country'])

    label_text = f"""
        Absender:
        {label_settings['sender_name']}
        {label_settings['sender_street']}
        {label_settings['sender_postalcode']} {label_settings['sender_city']}
        {label_settings['sender_country']}
        
        Empfänger:
        {order['shipping']['first_name']} {order['shipping']['last_name']}
        {order['shipping']['address_1']}
        {order['shipping']['postcode']} {order['shipping']['city']}
        {country}
    """
    
    text_position = (100, 5)
    text_color = (0, 0, 0)
    draw.text(text_position, label_text, font=font, fill=text_color)
    
    rotated_label = label_image.rotate(90, expand=True)
    new_image.paste(rotated_label, (0, 0), rotated_label)
    
    new_image.save(output_file)


def order_check(app_config: AppConfig) -> None:
    for order in app_config.woocommerce_api.get('orders').json():
        folder_name = f'order#{order["id"]}'
        if find_folder_in_subdirectories(app_config.input_folder, folder_name):
            if not is_order_already_completed(order):
                order_path = find_folder_path_in_subdirectories(app_config.input_folder, folder_name)
                order['order_path'] = order_path
                
                skin_file_paths = get_skin_file_paths(order_path, order['line_items'])
                for order_item, skin_file_path in zip(order['line_items'], skin_file_paths):
                    order_item['file_path'] = skin_file_path
                
                start_printing(order, app_config.label_settings)
                
                
def create_pdf_with_svg_and_png(png_path, svg_path, output_pdf_path):
    doc = fitz.open()
    page = doc.new_page(width=1327, height=705)

    img = Image.open(png_path)
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    page.insert_image(page.rect, stream=img_buffer.getvalue())

    svg_pdf = cairosvg.svg2pdf(url=svg_path)
    overlay_pdf = fitz.open("pdf", svg_pdf)
    page.show_pdf_page(page.rect, overlay_pdf, 0)

    doc.save(output_pdf_path)
    

def start_printing(order: dict, label_settings: dict) -> None:
    for item in order['line_items']:
        add_label_to_image(item['file_path'], item['file_path'].replace('stage-1.png', 'skin.png'), order, label_settings)
        create_pdf_with_svg_and_png(item['file_path'].replace('stage-1.png', 'skin.png'), 'cut/cut.svg', item['file_path'].replace('stage-1.png', 'skin.pdf'))
        
    set_order_completed(order)