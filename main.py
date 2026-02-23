from engine import DesignEngine
import sys, os, subprocess, cv2, numpy as np
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from database import DesignDB

class ImageCropper(QDialog):
    """Allows user to select the specific jersey area to ignore background noise."""
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Select Jersey Area")
        self.image_path = image_path
        self.img = cv2.imread(image_path)
        self.roi = None
        
        # Open standard OpenCV ROI selector
        # Instructions: Drag box, then press ENTER or SPACE. Press 'c' to cancel.
        self.roi = cv2.selectROI("Select Jersey Area - Press ENTER to Confirm", self.img)
        cv2.destroyWindow("Select Jersey Area - Press ENTER to Confirm")
        self.accept()

    def get_cropped_img(self):
        if self.roi and sum(self.roi) > 0:
            x, y, w, h = self.roi
            return self.img[y:y+h, x:x+w]
        return self.img

class DesignCard(QFrame):
    def __init__(self, file_path, score):
        super().__init__()
        self.file_path = file_path
        self.setFixedSize(300, 400)  # Slightly larger for better visibility
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Modern UI Styling with Laxpra Branding
        self.setStyleSheet("""
            QFrame {
                background-color: #eef2f7;
                border: 2px solid #fefefe;
                border-radius: 15px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
                background-color: #fcfdfe;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 2. IMAGE PREVIEW (Center)
        self.img_label = QLabel()
        self.img_label.setFixedSize(280, 280)
        self.img_label.setScaledContents(True)
        self.img_label.setStyleSheet("border-radius: 12px; background: #7408ef;")
        
        data = DesignEngine.get_preview_data(file_path)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            self.img_label.setPixmap(px)

        # 3. ACCURACY BADGE
        display_score = int(score * 100)
        score_lbl = QLabel(f"● {display_score}% Match")
        badge_color = "#27ae60" if display_score > 75 else "#f39c12"
        score_lbl.setStyleSheet(f"""
            color: {badge_color}; 
            font-weight: bold; 
            font-size: 12px;
            background: {badge_color}15; /* Transparent background */
            padding: 4px;
            border-radius: 5px;
        """)
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 4. FILE INFO (Bottom)
        name = QLabel(os.path.basename(file_path))
        name.setStyleSheet("font-size: 11px; color: #555; font-weight: 500;")
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assemble the Card
        layout.addWidget(self.img_label)
        layout.addWidget(score_lbl)
        layout.addWidget(name)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        path = os.path.normpath(self.file_path)
        if sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', path])
        else:
            subprocess.run(['xdg-open', os.path.dirname(path)])

class ScanThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, directory, db, engine):
        super().__init__()
        self.directory, self.db, self.engine = directory, db, engine

    def run(self):
        files_to_scan = []
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in {'AppData', 'Windows', '.git', 'venv'}]
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.cdr')):
                    files_to_scan.append(os.path.join(root, f))
        
        for i, path in enumerate(files_to_scan):
            feat = self.engine.get_features(path)
            if feat: self.db.add_design(path, feat)
            self.progress.emit(int((i + 1) / len(files_to_scan) * 100))
        self.finished.emit()

class DesignApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAXPRA - Perfect AI Matcher")
        self.resize(1000, 750)
        self.setAcceptDrops(True)
        self.db, self.engine = DesignDB(), DesignEngine()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        btns = QHBoxLayout()
        self.btn_index = QPushButton("📁 Step 1: Index Design Folder")
        self.btn_search = QPushButton("🔍 Step 2: Select Photo & Crop")
        self.btn_index.clicked.connect(self.scan_folder)
        self.btn_search.clicked.connect(self.select_and_crop)
        btns.addWidget(self.btn_index)
        btns.addWidget(self.btn_search)

        self.status = QLabel("Drag & Drop or use Step 2 to find a design.")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("padding: 15px; color: #fff; background: #667eea; border-radius: 5px; font-weight: 500;")
        
        self.pbar = QProgressBar()
        self.pbar.hide()

        self.scroll = QScrollArea()
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)

        layout.addLayout(btns)
        layout.addWidget(self.status)
        layout.addWidget(self.pbar)
        layout.addWidget(self.scroll)
        
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QPushButton { 
                height: 45px; 
                background: #667eea; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { 
                background: #5568d3; 
            }
            QPushButton:pressed {
                background: #4a5ac4;
            }
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #e0e0e0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #667eea;
                border-radius: 5px;
            }
            QScrollArea {
                border: none;
                background-color: #f8f9fa;
            }
        """)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].toLocalFile()
        self.search(path)

    def select_and_crop(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Design Image")
        if path:
            # 1. Open the cropper
            cropper = ImageCropper(path)
            cropped_img = cropper.get_cropped_img()
            
            # 2. Extract features directly from the cropped pixels
            # We temporarily save the cropped image or pass pixels to engine
            target_feat = self.engine.get_features_from_pixels(cropped_img)
            self.display_results(target_feat, os.path.basename(path))

    def scan_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Design Assets")
        if path:
            self.pbar.show()
            self.worker = ScanThread(path, self.db, self.engine)
            self.worker.progress.connect(self.pbar.setValue)
            self.worker.finished.connect(lambda: self.status.setText("Indexing Finished! Ready for Perfect Search."))
            self.worker.start()

    def search(self, path):
        target_feat = self.engine.get_features(path)
        if not target_feat: return
        
        # Clear existing results
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        all_data = self.db.get_all()
        matches = []
        for p, feat in all_data:
            score = self.engine.compare_designs(target_feat, feat)
            if score > 0.35: # Broaden threshold to find similar items
                matches.append((score, p))
        
        # Sort and take Top 10
        matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = matches[:10] 
        
        for i, (score, p) in enumerate(top_matches):
            # Display in 5 columns for a clean 2-row look
            self.grid.addWidget(DesignCard(p, score), i // 5, i % 5)
        
        self.status.setText(f"LAXPRA AI found {len(top_matches)} similar matches.")

    def display_results(self, target_feat, filename):
        if not target_feat:
            self.status.setText("Could not analyze image.")
            return

        # 1. Clear the current grid
        for i in reversed(range(self.grid.count())): 
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 2. Get all designs and calculate similarity scores
        all_data = self.db.get_all()
        matches = []
        for path, feat in all_data:
            score = self.engine.compare_designs(target_feat, feat)
            # Only show results with a decent match (above 30%)
            if score > 0.3: 
                matches.append((score, path))
        
        # 3. Sort by accuracy and take the Top 12 (to fill 3 rows of 4)
        matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = matches[:12]

        if not top_matches:
            self.status.setText("No similar designs found.")
            return

        # 4. Add the new "Design Cards" to the UI Grid
        for i, (score, path) in enumerate(top_matches):
            card = DesignCard(path, score)
            # Layout in 4 columns
            self.grid.addWidget(card, i // 4, i % 4)
            
        self.status.setText(f"Found {len(top_matches)} similar designs for '{filename}'")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DesignApp()
    win.show()
    sys.exit(app.exec())