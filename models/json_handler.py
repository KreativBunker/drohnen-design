import json
import os


class JSONHandler:
    @staticmethod
    def load(file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as json_file:
                return json.load(json_file)
        return {}

    @staticmethod
    def save(file_path, data):
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)