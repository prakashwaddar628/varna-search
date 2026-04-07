import cv2
import numpy as np
import zipfile
import os
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPVisionModelWithProjection

class DesignEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = "openai/clip-vit-base-patch32"
        print(f"Loading Semantic DL Engine ({self.model_id}) on {self.device}...")
        self.model = CLIPVisionModelWithProjection.from_pretrained(self.model_id).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.model_id)
        print("Model loaded successfully.")

    def get_features(self, file_path):
        try:
            def load_and_prep_img(f):
                img = Image.open(f)
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    alpha = img.convert('RGBA').split()[-1]
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=alpha)
                    return bg
                return img.convert('RGB')

            if isinstance(file_path, str) and file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    with archive.open('previews/preview.png') as thumb_file:
                        from io import BytesIO
                        img = load_and_prep_img(BytesIO(thumb_file.read()))
            else:
                img = load_and_prep_img(file_path)
            
            return self.get_features_from_pixels(img)
        except Exception as e:
            print(f"Extraction Error for {file_path}: {e}")
            return None

    def get_features_from_pixels(self, img):
        if img is None: return None
        
        try:
            # If it's a numpy array (from cv2 crop), convert to PIL Image
            if isinstance(img, np.ndarray):
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)

            inputs = self.processor(images=img, return_tensors="pt").to(self.device)
            with torch.no_grad():
                features = self.model(**inputs).image_embeds
            
            # Normalize the embedding for cosine similarity math
            features = features / features.norm(dim=-1, keepdim=True)
            
            return {
                "embedding": features.cpu().numpy().flatten().tolist()
            }
        except Exception as e:
            print(f"Internal Engine Error: {e}")
            return None

    def compare_designs(self, feat1, feat2):
        if not feat1 or not feat2 or 'embedding' not in feat1 or 'embedding' not in feat2:
            return {"score": 0.0, "bounds": None}

        e1 = np.array(feat1['embedding'])
        e2 = np.array(feat2['embedding'])
        
        # Cosine similarity is just the dot product because vectors are pre-normalized
        score = np.dot(e1, e2)
        
        return {
            "score": float(score),
            "bounds": None # Semantic matching doesn't use exact bounds
        }

    @staticmethod
    def get_preview_data(file_path):
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as archive:
                    return archive.read('previews/preview.png')
            with open(file_path, 'rb') as f: return f.read()
        except: return None