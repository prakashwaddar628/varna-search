import cv2
import numpy as np
import zipfile
import os
from PIL import Image

# Number of zones per axis — 4x4 = 16 spatial sections
ZONES = 4
# Number of histogram bins per HSV channel
H_BINS, S_BINS, V_BINS = 16, 8, 8


class DesignEngine:
    def __init__(self):
        print("Multi-Zone Color Engine Initialized (4x4 spatial grid, HSV histograms)")

    # -----------------------------------------------------------------
    # Internal: compute histograms for all zones of a PIL or numpy image
    # -----------------------------------------------------------------
    def _compute_zone_histograms(self, img_bgr: np.ndarray) -> list:
        """Divide image into a ZONES×ZONES grid and return one normalized
        HSV histogram per zone (list of numpy arrays)."""
        h, w = img_bgr.shape[:2]
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        zone_h = max(h // ZONES, 1)
        zone_w = max(w // ZONES, 1)

        histograms = []
        for row in range(ZONES):
            for col in range(ZONES):
                y1 = row * zone_h
                y2 = y1 + zone_h if row < ZONES - 1 else h
                x1 = col * zone_w
                x2 = x1 + zone_w if col < ZONES - 1 else w

                zone = hsv[y1:y2, x1:x2]
                hist = cv2.calcHist(
                    [zone], [0, 1, 2], None,
                    [H_BINS, S_BINS, V_BINS],
                    [0, 180, 0, 256, 0, 256]
                )
                cv2.normalize(hist, hist)
                histograms.append(hist.flatten().tolist())

        return histograms  # length == ZONES * ZONES

    # -----------------------------------------------------------------
    # Public: load image from path (supports jpg, png, cdr)
    # -----------------------------------------------------------------
    def get_features(self, file_path: str) -> dict | None:
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as arc:
                    with arc.open('previews/preview.png') as f:
                        data = np.frombuffer(f.read(), np.uint8)
                        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            else:
                img = cv2.imread(file_path)

            return self._extract(img)
        except Exception as e:
            print(f"Extraction Error [{file_path}]: {e}")
            return None

    # -----------------------------------------------------------------
    # Public: extract from raw numpy pixels (from cv2 crop / drag-drop)
    # -----------------------------------------------------------------
    def get_features_from_pixels(self, img) -> dict | None:
        """Accept a numpy BGR array or PIL Image."""
        try:
            if isinstance(img, Image.Image):
                img = cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)
            return self._extract(img)
        except Exception as e:
            print(f"Pixel Extraction Error: {e}")
            return None

    def _extract(self, img: np.ndarray) -> dict | None:
        if img is None:
            return None
        # Resize to standard size so zone counts are consistent
        img = cv2.resize(img, (320, 320))
        zones = self._compute_zone_histograms(img)
        return {"zones": zones}

    # -----------------------------------------------------------------
    # Public: compare two feature dicts, return score 0-1
    # -----------------------------------------------------------------
    def compare_designs(self, feat1: dict, feat2: dict) -> dict:
        if not feat1 or not feat2 or "zones" not in feat1 or "zones" not in feat2:
            return {"score": 0.0, "bounds": None}

        z1 = feat1["zones"]
        z2 = feat2["zones"]

        total = 0.0
        count = min(len(z1), len(z2))
        for h1, h2 in zip(z1, z2):
            a = np.array(h1, dtype=np.float32)
            b = np.array(h2, dtype=np.float32)
            # Bhattacharyya coefficient — 1 = identical, 0 = no overlap
            norm_a = np.sqrt(a / (a.sum() + 1e-8))
            norm_b = np.sqrt(b / (b.sum() + 1e-8))
            bc = float(np.dot(norm_a, norm_b))
            total += bc

        score = total / count if count > 0 else 0.0
        return {"score": score, "bounds": None}

    # -----------------------------------------------------------------
    # Public: load raw bytes for preview (used by UI cards)
    # -----------------------------------------------------------------
    @staticmethod
    def get_preview_data(file_path: str) -> bytes | None:
        try:
            if file_path.lower().endswith('.cdr'):
                with zipfile.ZipFile(file_path, 'r') as arc:
                    return arc.read('previews/preview.png')
            with open(file_path, 'rb') as f:
                return f.read()
        except:
            return None