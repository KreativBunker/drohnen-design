from dotenv import load_dotenv
from woocommerce import API

import os


class AppConfig:
    
    
    def __init__(self):
        
        load_dotenv()
        
        self.base_url = os.getenv('URL')
        self.consumer_key = os.getenv('CONSUMER_KEY')
        self.consumer_secret = os.getenv('CONSUMER_SECRET')
        self.sender_name = os.getenv('SENDER_NAME')
        self.sender_street = os.getenv('SENDER_STREET')
        self.sender_postalcode = os.getenv('SENDER_POSTALCODE')
        self.sender_city = os.getenv('SENDER_CITY')
        self.sender_country = os.getenv('SENDER_COUNTRY')
        
        self.label_settings = {
            'sender_name': self.sender_name,
            'sender_street': self.sender_street,
            'sender_postalcode': self.sender_postalcode,
            'sender_city': self.sender_city,
            'sender_country': self.sender_country
        }
        
        self.input_folder = 'Drohnen-Design'

        self.woocommerce_api = API(
            url=self.base_url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version='wc/v3'
        )