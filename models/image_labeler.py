from PIL import Image, ImageDraw, ImageFont

import pycountry


class ImageLabeler:
    def __init__(self, label_settings):
        self.label_settings = label_settings

    def add_label(self, input_file, output_file, order):
        image = Image.open(input_file).convert('RGBA')
        new_width = image.width + (168 * 3)
        new_image = Image.new("RGBA", (new_width, image.height), (255, 255, 255, 0))
        new_image.paste(image, ((168 * 3), 0))

        label_image = Image.new("RGBA", (new_width, image.height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(label_image)
        font_normal = ImageFont.truetype(self.label_settings['text_font_path'], self.label_settings['text_font_size'] * 3)
        font_bold = ImageFont.truetype(self.label_settings['text_bold_font_path'], self.label_settings['text_font_size'] * 3)
        country = pycountry.countries.get(alpha_2=order['shipping']['country']).name if order['shipping']['country'] else ''

        sender_position = tuple(map(int, self.label_settings['text_sender_pos'].split(',')))
        receiver_position = tuple(map(int, self.label_settings['text_receiver_pos'].split(',')))

        draw.text((sender_position[0] * 3, sender_position[1]), "Absender:", font=font_bold, fill=(0, 0, 0))
        draw.text((receiver_position[0] * 3, receiver_position[1]), "Empfänger:", font=font_bold, fill=(0, 0, 0))
        new_image.paste(label_image, (0, 0), label_image)
        new_image.save(output_file, format='PNG', compress_level=0)