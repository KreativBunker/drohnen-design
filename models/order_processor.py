from models.image_labeler import ImageLabeler
from models.json_handler import JSONHandler
from models.pdf_creator import PDFCreator

import shutil
import time
import os


class OrderProcessor:
    def __init__(self, woocommerce_api, settings, ftp_handler):
        self.woocommerce_api = woocommerce_api
        self.hotfolder_path = settings['hotfolder_path']
        self.label_settings = settings['label_settings']
        self.ftp_handler = ftp_handler
        self.image_labeler = ImageLabeler(settings['label_settings'])

    def is_order_in_status(self, order, status_file):
        orders_data = JSONHandler.load(status_file)
        return order['id'] in [o['id'] for o in orders_data.get('data', [])]

    def set_order_status(self, order, status_file):
        orders_data = JSONHandler.load(status_file)
        if 'data' not in orders_data:
            orders_data['data'] = []
        orders_data['data'].append(order)
        JSONHandler.save(status_file, orders_data)

    def process_orders(self):
        for order in self.woocommerce_api.get_orders():
            if not self.is_order_in_status(order, 'orders_failed.json'):
                error_attempts = 0
                while True:
                    try:
                        if not self.is_order_in_status(order, 'orders_completed.json'):
                            self.process_order_items(order)
                        break
                    except Exception:
                        print(f'Order({order["id"]}) failed to print, retrying...')
                        error_attempts += 1
                        time.sleep(5)
                    if error_attempts >= 3:
                        self.set_order_status(order, 'orders_failed.json')
                        print(f'Order({order["id"]}) failed')
                        break

    def process_order_items(self, order):
        for item in order['line_items']:
            if 'file_path' not in item:
                continue
            self.image_labeler.add_label(item['file_path'], item['file_path'].replace('stage-1.png', 'skin.png'), order)
            PDFCreator.create_with_overlay(item['file_path'].replace('stage-1.png', 'skin.png'), 'cuts/cut.pdf',
                                           item['file_path'].replace('stage-1.png', 'skin.pdf'))
            shutil.copy2(item['file_path'].replace('stage-1.png', 'skin.pdf'),
                  f'{self.hotfolder_path}/skin_{item["id"]}.pdf')
            os.remove(item['file_path'])
            processed = True
            print('done')
        
        if processed:
            self.set_order_status(order, 'orders_completed.json')
            print(f'Order({order["id"]}) completed')
        else:
            Exception(f'Order({order["id"]}) failed')