from models.woocommerce_api import WooCommerceAPI
from models.order_processor import OrderProcessor
from models.ftp_handler import FTPHandler

from dotenv import load_dotenv

import traceback
import time
import os


def main():
    load_dotenv(override=True)
    
    woocommerce = WooCommerceAPI(
        url=os.getenv('URL'),
        consumer_key=os.getenv('CONSUMER_KEY'),
        consumer_secret=os.getenv('CONSUMER_SECRET')
    )
    
    label_settings = {
        'text_font_path': os.getenv('TEXT_FONT_PATH'),
        'text_bold_font_path': os.getenv('TEXT_BOLD_FONT_PATH'),
        'text_font_size': os.getenv('TEXT_FONT_SIZE'),
        'text_sender_pos': os.getenv('TEXT_SENDER_POS'),
        'text_receiver_pos': os.getenv('TEXT_RECEIVER_POS'),
        'sender_name': os.getenv('SENDER_NAME'),
        'sender_street': os.getenv('SENDER_STREET'),
        'sender_postalcode': os.getenv('SENDER_POSTALCODE'),
        'sender_city': os.getenv('SENDER_CITY'),
        'sender_country': os.getenv('SENDER_COUNTRY')
    }
    
    ftp_handler = FTPHandler(
        server=os.getenv('FTP_SERVER'),
        username=os.getenv('FTP_USERNAME'),
        password=os.getenv('FTP_PASSWORD')
    )
    
    order_processor = OrderProcessor(woocommerce, label_settings, ftp_handler)
    
    while True:
        try:
            order_processor.process_orders()
        except Exception as error:
            print(f"Error processing orders: {error}")
            traceback.print_exc()
        time.sleep(5)


if __name__ == '__main__':
    main()
