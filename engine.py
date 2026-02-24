import cv2
import numpy as np
import zipfile
import os

class DesignEngine:
    def __init__(self):
        # Limit SIFT to 1000 features to prevent memory bloat
        self.sift = cv2.SIFT_create(nfeatures=1000)
        print("Memory-Safe High-Accuracy Engine Initialized")

    def get_features(self, file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    with archive.open('previews/preview.png') as thumb_file:
                        img_data = np.frombuffer(thumb_file.read(), np.uint8)
                        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
            else:
                img = cv2.imread(file_path)
            
            return self.get_features_from_pixels(img)
        except Exception as e:
            print(f"Extraction Error: {e}")
            return None

    def get_features_from_pixels(self, img):
        if img is None: return None
        
        try:
            # CRITICAL: Resize image to prevent OutOfMemoryError
            # We resize while keeping aspect ratio, max width 600px
            h, w = img.shape[:2]
            scale = 600 / max(h, w)
            img_small = cv2.resize(img, (int(w * scale), int(h * scale)))

            # 1. Texture (SIFT)
            gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
            kp, des = self.sift.detectAndCompute(gray, None)
            
            # 2. Color (Histogram)
            hsv = cv2.cvtColor(img_small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
            cv2.normalize(hist, hist)
            
            # Clean up memory
            del img_small
            del gray
            
            return {
                "descriptors": des.tolist() if des is not None else None,
                "color": hist.flatten().tolist()
            }
        except Exception as e:
            print(f"Internal Engine Error: {e}")
            return None

    def compare_designs(self, feat1, feat2):
        if not feat1 or not feat2 or not isinstance(feat1, dict): return 0.0

        # A. Color Similarity
        c1, c2 = np.array(feat1['color']), np.array(feat2['color'])
        color_score = np.dot(c1, c2) / (np.linalg.norm(c1) * np.linalg.norm(c2))

        # B. Pattern Similarity
        pattern_score = 0.0
        if feat1['descriptors'] and feat2['descriptors']:
            d1 = np.array(feat1['descriptors'], dtype=np.float32)
            d2 = np.array(feat2['descriptors'], dtype=np.float32)
            
            # Using Brute Force for stability in bundled apps
            bf = cv2.BFMatcher()
            matches = bf.knnMatch(d1, d2, k=2)
            
            # Ratio Test
            good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]
            pattern_score = len(good_matches) / 60.0 # Adjusted sensitivity

        # 30% Color, 70% Pattern
        final_score = (color_score * 0.3) + (min(pattern_score, 1.0) * 0.7)
        return float(final_score)

    @staticmethod
    def get_preview_data(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            with open(file_path, 'rb') as f: return f.read()
        except: return None