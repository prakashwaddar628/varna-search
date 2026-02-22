import sys, os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QFileDialog, QScrollArea, QProgressBar, QGridLayout, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from database import DesignDB
from engine import DesignEngine

class DesignCard(QFrame):
    def __init__(self, file_path, score):
        super().__init__()
        self.setFixedSize(170, 220)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; color: white; border: 1px solid #444;")
        layout = QVBoxLayout()
        
        img_label = QLabel()
        img_label.setFixedSize(150, 150)
        img_label.setScaledContents(True)
        
        # Load Preview
        engine = DesignEngine()
        data = engine.get_preview_data(file_path)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            img_label.setPixmap(px)
        else:
            img_label.setText("No Preview")

        name = QLabel(os.path.basename(file_path))
        name.setStyleSheet("font-size: 10px; font-weight: bold;")
        score_lbl = QLabel(f"Match Score: {max(0, 100-score)}%")
        score_lbl.setStyleSheet("color: #00FF7F;")

        layout.addWidget(img_label)
        layout.addWidget(name)
        layout.addWidget(score_lbl)
        self.setLayout(layout)

class ScanThread(QThread):
    progress = pyqtSignal(int)
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
            h = self.engine.get_image_hash(path)
            if h: self.db.add_design(path, h)
            self.progress.emit(int((i + 1) / len(files_to_scan) * 100))

class DesignApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Varna Search - Jersey & Design Finder")
        self.resize(1000, 750)
        self.setAcceptDrops(True)
        self.db, self.engine = DesignDB(), DesignEngine()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.status = QLabel("Drag & Drop Image here to find similar designs")
        self.status.setStyleSheet("padding: 20px; border: 2px dashed #555; font-size: 18px;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pbar = QProgressBar()
        btn = QPushButton("Index/Scan Folder")
        btn.clicked.connect(self.scan_folder)

        self.scroll = QScrollArea()
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)

        layout.addWidget(self.status)
        layout.addWidget(self.pbar)
        layout.addWidget(btn)
        layout.addWidget(self.scroll)
        
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; } QPushButton { height: 40px; background: #444; color: white; border-radius: 5px; }")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].toLocalFile()
        self.search(path)

    def scan_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.worker = ScanThread(path, self.db, self.engine)
            self.worker.progress.connect(self.pbar.setValue)
            self.worker.start()

    def search(self, path):
        target_h = self.engine.get_image_hash(path)
        if not target_h: return
        
        # Clear Grid
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        results = self.db.get_all()
        matches = []
        for p, h in results:
            dist = self.engine.compare_hashes(target_h, h)
            if dist < 16: matches.append((dist, p))
        
        matches.sort()
        for i, (dist, p) in enumerate(matches):
            self.grid.addWidget(DesignCard(p, dist), i // 5, i % 5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DesignApp()
    win.show()
    sys.exit(app.exec())