from dotenv import load_dotenv
from woocommerce import API
from utils import *

import time
import os


if __name__ == '__main__':
    load_dotenv()
    
    URL = os.getenv('URL')
    CONSUMER_KEY = os.getenv('CONSUMER_KEY')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
    
    SENDER_NAME = os.getenv('SENDER_NAME')
    SENDER_STREET = os.getenv('SENDER_STREET')
    SENDER_POSTALCODE = os.getenv('SENDER_POSTALCODE')
    SENDER_CITY = os.getenv('SENDER_CITY')
    SENDER_COUNTRY = os.getenv('SENDER_COUNTRY')
    
    LABEL_SETTINGS = {
        'sender_name': SENDER_NAME,
        'sender_street': SENDER_STREET,
        'sender_postalcode': SENDER_POSTALCODE,
        'sender_city': SENDER_CITY,
        'sender_country': SENDER_COUNTRY
    }
    
    INPUT_FOLDER = 'Drohnen-Design'

    WOOCOMMERCE_API = API(
        url=URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version='wc/v3'
    )
    
    order_check(WOOCOMMERCE_API, INPUT_FOLDER, LABEL_SETTINGS)