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
        self.setFixedSize(180, 250)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 12px; border: 2px solid #444;")
        
        layout = QVBoxLayout()
        img_label = QLabel()
        img_label.setFixedSize(160, 160)
        img_label.setScaledContents(True)
        
        data = DesignEngine.get_preview_data(file_path)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            img_label.setPixmap(px)
        
        name = QLabel(os.path.basename(file_path))
        name.setStyleSheet("font-size: 11px; color: #ddd; font-weight: bold;")
        name.setWordWrap(True)
        
        display_score = int(score * 100)
        score_lbl = QLabel(f"Match Accuracy: {display_score}%")
        color = "#00FF7F" if display_score > 75 else "#FFA500"
        score_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

        layout.addWidget(img_label)
        layout.addWidget(name)
        layout.addWidget(score_lbl)
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
        self.setWindowTitle("Varna Search - Perfect AI Matcher")
        self.resize(1100, 850)
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
        self.status.setStyleSheet("padding: 15px; color: #aaa; background: #1a1a1a; border-radius: 5px;")
        
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
            QMainWindow { background-color: #121212; }
            QPushButton { height: 45px; background: #333; color: white; border: 1px solid #555; border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: #444; border: 1px solid #777; }
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
        # Default search (no cropping) for Drag & Drop
        target_feat = self.engine.get_features(path)
        self.display_results(target_feat, os.path.basename(path))

    def display_results(self, target_feat, filename):
        if not target_feat:
            self.status.setText("Could not analyze image.")
            return

        # Clear grid
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        all_data = self.db.get_all()
        matches = []
        for p, feat in all_data:
            score = self.engine.compare_designs(target_feat, feat)
            if score > 0.4: 
                matches.append((score, p))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        for i, (score, p) in enumerate(matches[:20]):
            self.grid.addWidget(DesignCard(p, score), i // 4, i % 4)
        
        self.status.setText(f"Found {len(matches)} matches for '{filename}'. Top results are most accurate.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DesignApp()
    win.show()
    sys.exit(app.exec())