import imagehash
from PIL import Image
import zipfile
import io
import numpy as np # Make sure to: pip install numpy

class DesignEngine:
    def get_features(self, file_path):
        """Extracts both Pattern (Hash) and Color info"""
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    with archive.open('previews/preview.png') as thumb_file:
                        img = Image.open(io.BytesIO(thumb_file.read())).convert('RGB')
            else:
                img = Image.open(file_path).convert('RGB')
            
            # 1. Pattern Hash
            p_hash = str(imagehash.phash(img))
            
            # 2. Color Histogram (Simplified for speed)
            img_small = img.resize((100, 100))
            hist = np.array(img_small.histogram())
            hist = hist / hist.sum() # Normalize
            
            return {"hash": p_hash, "hist": hist.tolist()}
        except:
            return None

    def compare_designs(self, feat1, feat2):
        """Returns a similarity score (Lower is better)"""
        # Compare Patterns
        h1 = imagehash.hex_to_hash(feat1['hash'])
        h2 = imagehash.hex_to_hash(feat2['hash'])
        hash_diff = h1 - h2
        
        # Compare Colors
        hist1 = np.array(feat1['hist'])
        hist2 = np.array(feat2['hist'])
        color_diff = np.linalg.norm(hist1 - hist2) * 100
        
        # Combined Score (60% Color + 40% Pattern works best for Photos)
        return (hash_diff * 0.4) + (color_diff * 0.6)

    @staticmethod
    def get_preview_data(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            with open(file_path, 'rb') as f: return f.read()
        except: return None