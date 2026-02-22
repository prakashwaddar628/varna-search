import imagehash
from PIL import Image
import zipfile
import io
import os

class DesignEngine:
    @staticmethod
    def get_image_hash(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    with archive.open('previews/preview.png') as thumb_file:
                        img = Image.open(io.BytesIO(thumb_file.read()))
            else:
                img = Image.open(file_path)
            return str(imagehash.phash(img))
        except:
            return None

    @staticmethod
    def get_preview_data(file_path):
        """Returns image bytes for the UI to display thumbnails"""
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            else:
                with open(file_path, 'rb') as f:
                    return f.read()
        except:
            return None

    @staticmethod
    def compare_hashes(hash1, hash2):
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2