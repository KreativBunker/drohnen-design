from typing import Optional

import os


class FileManager:
    def __init__(self, root_path: str):
        self.root_path = root_path
    
    def find_folder(self, target_folder_name: str) -> bool:
        for _, dirnames, _ in os.walk(self.root_path):
            if target_folder_name in dirnames:
                return True
        return False
    
    def get_folder_path(self, target_folder_name: str) -> Optional[str]:
        for dirpath, dirnames, _ in os.walk(self.root_path):
            if target_folder_name in dirnames:
                return os.path.join(dirpath, target_folder_name)
        return None