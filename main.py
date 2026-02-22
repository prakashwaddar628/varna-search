import sys, os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QFileDialog, QScrollArea, QProgressBar, 
                             QGridLayout, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from database import DesignDB
from engine import DesignEngine

class DesignCard(QFrame):
    def __init__(self, file_path, score):
        super().__init__()
        self.setFixedSize(170, 230)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; color: white; border: 1px solid #444;")
        layout = QVBoxLayout()
        img_label = QLabel()
        img_label.setFixedSize(150, 150)
        img_label.setScaledContents(True)
        
        data = DesignEngine.get_preview_data(file_path)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            img_label.setPixmap(px)
        else:
            img_label.setText("No Preview")

        name = QLabel(os.path.basename(file_path))
        name.setStyleSheet("font-size: 10px;")
        name.setWordWrap(True)
        
        score_val = max(0, 100 - int(score * 2)) # Adjusted for display
        score_lbl = QLabel(f"Match: {score_val}%")
        score_lbl.setStyleSheet("color: #00FF7F; font-weight: bold;")

        layout.addWidget(img_label)
        layout.addWidget(name)
        layout.addWidget(score_lbl)
        self.setLayout(layout)

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
        self.setWindowTitle("Varna Search - Professional Design Finder")
        self.resize(1100, 800)
        self.setAcceptDrops(True)
        self.db, self.engine = DesignDB(), DesignEngine()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        btns = QHBoxLayout()
        self.btn_index = QPushButton("📁 Index Folder")
        self.btn_search = QPushButton("🔍 Select WhatsApp Image")
        self.btn_index.clicked.connect(self.scan_folder)
        self.btn_search.clicked.connect(self.select_file)
        btns.addWidget(self.btn_index)
        btns.addWidget(self.btn_search)

        self.status = QLabel("Drag & Drop or use the buttons above to start")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("padding: 20px; border: 2px dashed #555; background: #222; color: #888;")
        
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
        self.setStyleSheet("QMainWindow { background-color: #121212; } QPushButton { height: 40px; background: #333; color: white; }")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].toLocalFile()
        self.search(path)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image")
        if path: self.search(path)

    def scan_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.pbar.show()
            self.worker = ScanThread(path, self.db, self.engine)
            self.worker.progress.connect(self.pbar.setValue)
            self.worker.finished.connect(lambda: self.status.setText("Indexing Complete! Ready to search."))
            self.worker.start()

    def search(self, path):
        target_feat = self.engine.get_features(path)
        if not target_feat: return
        
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        all_data = self.db.get_all()
        matches = []
        for p, feat in all_data:
            score = self.engine.compare_designs(target_feat, feat)
            if score < 35: # Threshold for photo-to-design matching
                matches.append((score, p))
        
        matches.sort()
        for i, (score, p) in enumerate(matches[:20]): # Show top 20
            self.grid.addWidget(DesignCard(p, score), i // 5, i % 5)
        self.status.setText(f"Found {len(matches)} potential matches.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DesignApp()
    win.show()
    sys.exit(app.exec())