import sys, os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QLabel, QFileDialog, QScrollArea, QProgressBar, 
                             QGridLayout, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
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
        
        # Load Preview logic from engine
        engine = DesignEngine()
        data = engine.get_preview_data(file_path)
        if data:
            px = QPixmap()
            px.loadFromData(data)
            img_label.setPixmap(px)
        else:
            img_label.setText("No Preview")
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel(os.path.basename(file_path))
        name.setStyleSheet("font-size: 10px; font-weight: bold;")
        name.setWordWrap(True)
        
        score_lbl = QLabel(f"Match: {max(0, 100-score)}%")
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
            dirs[:] = [d for d in dirs if d not in {'AppData', 'Windows', '.git', 'venv', '__pycache__'}]
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.cdr')):
                    files_to_scan.append(os.path.join(root, f))
        
        for i, path in enumerate(files_to_scan):
            h = self.engine.get_image_hash(path)
            if h: self.db.add_design(path, h)
            self.progress.emit(int((i + 1) / len(files_to_scan) * 100))
        self.finished.emit()

class DesignApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Varna Search - Jersey & Design Finder")
        self.resize(1100, 800)
        self.setAcceptDrops(True)
        self.db, self.engine = DesignDB(), DesignEngine()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # Top Controls (Horizontal)
        top_bar = QHBoxLayout()
        
        self.btn_scan = QPushButton("📁 Index Folder (Add Designs)")
        self.btn_scan.clicked.connect(self.scan_folder)
        
        self.btn_select = QPushButton("🔍 Select WhatsApp Image")
        self.btn_select.setStyleSheet("background-color: #056162; font-weight: bold;") # WhatsApp Green
        self.btn_select.clicked.connect(self.select_image_manually)
        
        top_bar.addWidget(self.btn_scan)
        top_bar.addWidget(self.btn_select)

        # Drop Area
        self.status = QLabel("DRAG & DROP IMAGE HERE\nor use the button above")
        self.status.setStyleSheet("""
            QLabel {
                padding: 30px; 
                border: 2px dashed #777; 
                font-size: 14px; 
                color: #aaa; 
                background-color: #252525;
                border-radius: 10px;
            }
        """)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pbar = QProgressBar()
        self.pbar.hide() # Hide until scanning

        # Results Grid
        self.scroll = QScrollArea()
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)

        main_layout.addLayout(top_bar)
        main_layout.addWidget(self.status)
        main_layout.addWidget(self.pbar)
        main_layout.addWidget(self.scroll)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Global Styling
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QPushButton { 
                height: 45px; 
                background-color: #333; 
                color: white; 
                border-radius: 5px; 
                padding: 5px 15px; 
            }
            QPushButton:hover { background-color: #444; }
            QProgressBar { border: 1px solid grey; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #056162; }
        """)

    # --- Interaction Logic ---
    def select_image_manually(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.cdr)")
        if path:
            self.search(path)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].toLocalFile()
        self.search(path)

    def scan_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Index")
        if path:
            self.pbar.show()
            self.status.setText("Indexing files... Please wait.")
            self.worker = ScanThread(path, self.db, self.engine)
            self.worker.progress.connect(self.pbar.setValue)
            self.worker.finished.connect(lambda: self.status.setText("Indexing Complete! Ready to search."))
            self.worker.start()

    def search(self, path):
        target_h = self.engine.get_image_hash(path)
        if not target_h: 
            self.status.setText("Error: Could not process that image.")
            return
        
        # Clear existing grid results
        for i in reversed(range(self.grid.count())): 
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        results = self.db.get_all()
        print(f"Total designs in database: {len(results)}") # DEBUG LINE
        
        matches = []
        for p, h in results:
            dist = self.engine.compare_hashes(target_h, h)
            # RELAXED THRESHOLD: Increased from 16 to 24
            # 0 = identical, 64 = completely different.
            if dist < 24: 
                matches.append((dist, p))
        
        print(f"Found {len(matches)} matches") # DEBUG LINE
        
        if not matches:
            self.status.setText("No similar designs found. Try indexing more folders.")
        else:
            self.status.setText(f"Found {len(matches)} matches for: {os.path.basename(path)}")
            matches.sort()
            for i, (dist, p) in enumerate(matches):
                self.grid.addWidget(DesignCard(p, dist), i // 5, i % 5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DesignApp()
    win.show()
    sys.exit(app.exec())