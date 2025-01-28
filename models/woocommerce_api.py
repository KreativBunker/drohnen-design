from woocommerce import API


class WooCommerceAPI:
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        self.api = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version='wc/v3'
        )
    
    def get_orders(self):
        return self.api.get('orders').json()