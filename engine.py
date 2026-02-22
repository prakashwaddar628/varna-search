import cv2
import numpy as np
import zipfile
import io
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class DesignEngine:
    def __init__(self):
        # We use Google's professional Mobilenet_v3 model for embeddings
        # You can download the 'mobilenet_v3_small.tflite' model from Google's AI Edge site
        # Or I can help you use a built-in OpenCV alternative if you prefer no downloads.
        self.model_path = 'embedder.tflite'
        
        if not os.path.exists(self.model_path):
            print("AI Model (embedder.tflite) not found. System will use classic math search.")
            self.embedder = None
        else:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = vision.ImageEmbedderOptions(base_options=base_options, l2_normalize=True)
            self.embedder = vision.ImageEmbedder.create_from_options(options)

    def get_features(self, file_path):
        """Extracts AI Visual DNA using Google's MediaPipe."""
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
            print(f"AI Extraction Error: {e}")
            return None

    def get_features_from_pixels(self, img):
        """Processes images into AI vectors (Google Search Style)."""
        if img is None: return None
        
        # If the AI model is missing, we fall back to a high-accuracy color pattern
        if self.embedder is None:
            return self._fallback_math_features(img)

        # AI Processing
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        embedding_result = self.embedder.embed(mp_image)
        return embedding_result.embeddings[0].float_embedding.tolist()

    def _fallback_math_features(self, img):
        """A robust 'Custom AI' built from math to ensure search always works."""
        img = cv2.resize(img, (256, 256))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten().tolist()

    def compare_designs(self, feat1, feat2):
        """Standard AI Similarity (Cosine)."""
        f1, f2 = np.array(feat1), np.array(feat2)
        score = np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))
        return float(score)

    @staticmethod
    def get_preview_data(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            with open(file_path, 'rb') as f: return f.read()
        except: return None