import tkinter as tk


processor = None


def start_processing():
    """Start the order processing thread and update button states."""
    global processor
    # Import locally to avoid heavy dependencies at module import time
    import os
    from dotenv import load_dotenv
    from woocommerce import API
    from run import OrderProcessor

    load_dotenv(override=True)

    url = os.getenv('URL')
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    hotfolder_path = os.getenv('HOTFOLDER_PATH')

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

    api = API(
        url=url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version='wc/v3'
    )

    processor = OrderProcessor(api, label_settings, hotfolder_path, url)
    processor.start()

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


def stop():
    """Stop the order processing thread and reset button states."""
    global processor
    if processor:
        processor.stop()
    stop_button.config(state=tk.DISABLED)
    start_button.config(state=tk.NORMAL)


root = tk.Tk()
root.title('Drohnen Design')

start_button = tk.Button(root, text='Start', command=start_processing)
start_button.pack(padx=10, pady=5)

stop_button = tk.Button(root, text='Stop', state=tk.DISABLED, command=stop)
stop_button.pack(padx=10, pady=5)

root.mainloop()
