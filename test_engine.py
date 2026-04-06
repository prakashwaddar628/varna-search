import cv2
import numpy as np
import os
from engine import DesignEngine
from database import DesignDB

def create_test_images():
    img = np.zeros((600, 600, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (400, 400), (255, 0, 0), -1)
    cv2.circle(img, (300, 300), 100, (0, 255, 0), -1)
    cv2.putText(img, "CLIP TEST", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Save the "database" full image
    cv2.imwrite("test_full_noise.png", img)
    
    # Crop a region
    crop = img[50:250, 50:250]
    cv2.imwrite("test_crop_noise.png", crop)
    print("Created test_full_noise.png and test_crop_noise.png")

def test_engine():
    db = DesignDB()
    engine = DesignEngine()
    
    print("\n--- Indexing ---")
    feat_full = engine.get_features("test_full_noise.png")
    if feat_full:
        db.add_design("test_full_noise.png", feat_full)
        print("Indexed successfully.")
        print(f"Number of embedding dimensions: {len(feat_full['embedding'])}")

    print("\n--- Searching ---")
    feat_crop = engine.get_features("test_crop_noise.png")
    if feat_crop:
        print("Extracted crop features successfully.")
        
        all_data = db.get_all()
        for path, feat_db in all_data:
            if "noise" not in path: continue
            
            result = engine.compare_designs(feat_crop, feat_db)
            print(f"Match Score against {path}: {result['score']}")

if __name__ == "__main__":
    create_test_images()
    test_engine()
    
    if os.path.exists("test_full_noise.png"): os.remove("test_full_noise.png")
    if os.path.exists("test_crop_noise.png"): os.remove("test_crop_noise.png")
