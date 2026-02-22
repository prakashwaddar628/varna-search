import imagehash
from PIL import Image
import zipfile
import io
import numpy as np

class DesignEngine:
    @staticmethod
    def get_image_data(file_path):
        """Helper to get a PIL Image from .cdr or standard image"""
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    with archive.open('previews/preview.png') as thumb_file:
                        return Image.open(io.BytesIO(thumb_file.read())).convert('RGB')
            return Image.open(file_path).convert('RGB')
        except:
            return None

    def get_features(self, file_path):
        """Extracts both Hash (Pattern) and Histogram (Color)"""
        img = self.get_image_data(file_path)
        if img is None: return None
        
        # 1. Pattern Hash
        p_hash = str(imagehash.phash(img))
        
        # 2. Color Histogram (Simplified to 64 values for speed)
        img_small = img.resize((100, 100))
        hist = img_small.histogram()
        # Normalize histogram to make it independent of image size
        hist = np.array(hist) / sum(hist)
        
        return {"hash": p_hash, "hist": hist.tolist()}

    @staticmethod
    def compare_designs(target_features, saved_features):
        # 1. Compare Patterns (0 is perfect)
        h1 = imagehash.hex_to_hash(target_features['hash'])
        h2 = imagehash.hex_to_hash(saved_features['hash'])
        hash_dist = h1 - h2
        
        # 2. Compare Colors (0 is perfect)
        hist1 = np.array(target_features['hist'])
        hist2 = np.array(saved_features['hist'])
        color_dist = np.linalg.norm(hist1 - hist2) * 100 # Euclidean distance
        
        # Combined Score: We give more weight to color for T-shirt photos
        # because the 'pattern' is often distorted by wrinkles.
        final_score = (hash_dist * 0.4) + (color_dist * 0.6)
        return final_score

    @staticmethod
    def get_preview_data(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            with open(file_path, 'rb') as f: return f.read()
        except: return None