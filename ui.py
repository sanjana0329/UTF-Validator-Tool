import sys
import os
import csv
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame,
    QScrollArea, QHBoxLayout, QProgressBar, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from validator import scan_single_file, scan_folder


# ---------------- Animation Thread ----------------
class AnimThread(QThread):
    tick = pyqtSignal()

    def run(self):
        while not self.isInterruptionRequested():
            self.msleep(1000)
            if not self.isInterruptionRequested():
                self.tick.emit()


# ---------------- Worker Thread ----------------
class ScanThread(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, file_path=None, folder_path=None):
        super().__init__()
        self.file_path = file_path
        self.folder_path = folder_path

    def run(self):
        results = []
        utf_count     = 0
        non_utf_count = 0
        mixed_count   = 0
        binary_count  = 0
        total_utf_percent = 0.0

        def categorize(info):
            nonlocal utf_count, non_utf_count, mixed_count, binary_count, total_utf_percent
            if info.get("is_binary"):
                binary_count += 1
            elif info["is_utf"]:
                utf_count += 1
            elif info["is_mostly_utf"]:
                mixed_count += 1
            else:
                non_utf_count += 1
            total_utf_percent += info["utf_percent"]

        if self.file_path:
            info = scan_single_file(self.file_path)
            info["filename"] = os.path.basename(self.file_path)
            info["file"]     = self.file_path
            results.append(info)
            categorize(info)

        elif self.folder_path:
            all_files = []
            for root, dirs, files in os.walk(self.folder_path):
                for f in files:
                    all_files.append(os.path.join(root, f))
            for full_path in all_files:
                info = scan_single_file(full_path)
                info["file"]     = full_path
                info["filename"] = os.path.basename(full_path)
                results.append(info)
                categorize(info)

        avg_utf = round(total_utf_percent / len(results), 1) if results else 0.0

        self.finished_signal.emit({
            "results":         results,
            "utf":             utf_count,
            "non_utf":         non_utf_count,
            "mixed":           mixed_count,
            "binary":          binary_count,
            "total":           len(results),
            "avg_utf_percent": avg_utf
        })


# ---------------- Animated Loader Widget ----------------
class LoaderWidget(QFrame):
    FRAMES = [
        ("🕵️", "Detecting encodings..."),
        ("🔬", "Checking UTF validity..."),
        ("🚀", "Almost there..."),
        ("✨", "Wrapping things up..."),
        ("🎯", "Finalizing results..."),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._index = 0
        self.setStyleSheet("QFrame { background: transparent; } QLabel { background: transparent; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        self.emoji_lbl = QLabel("🔍")
        self.emoji_lbl.setAlignment(Qt.AlignCenter)
        self.emoji_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self.emoji_lbl)

        self.text_lbl = QLabel("Sniffing out files...")
        self.text_lbl.setAlignment(Qt.AlignCenter)
        self.text_lbl.setStyleSheet("font-size: 14px; color: #60a5fa; font-weight: bold;")
        self.text_lbl.setWordWrap(True)
        layout.addWidget(self.text_lbl)

        self.setLayout(layout)
        self.hide()

    def start(self):
        self._index = 0
        self._show()
        self.show()

    def stop(self):
        self.hide()

    def next_frame(self):
        self._index = (self._index + 1) % len(self.FRAMES)
        self._show()

    def _show(self):
        emoji, text = self.FRAMES[self._index]
        self.emoji_lbl.setText(emoji)
        self.text_lbl.setText(text)


# ---------------- Main UI ----------------
class UTFValidatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UTF Validator Tool")
        self.selected_file   = None
        self.selected_folder = None
        self._last_results   = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #f5f7fb; font-family: Segoe UI; }")

        # ================= SIDEBAR =================
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(300)
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.sidebar.setStyleSheet("""
            QFrame { background-color: #1f2937; }
            QLabel { color: #e5e7eb; background: transparent; }
        """)

        sl = QVBoxLayout()
        sl.setContentsMargins(20, 30, 20, 20)
        sl.setSpacing(0)

        # Title
        title = QLabel("🔤  UTF Validator")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; background: transparent;")
        sl.addWidget(title)
        sl.addSpacing(4)
        subtitle = QLabel("Encoding Detection Tool")
        subtitle.setStyleSheet("font-size: 11px; color: #6b7280; background: transparent;")
        sl.addWidget(subtitle)
        sl.addSpacing(24)

        def divider():
            d = QFrame(); d.setFrameShape(QFrame.HLine)
            d.setStyleSheet("background-color: #374151; max-height: 1px; margin: 0px;")
            return d

        sl.addWidget(divider())
        sl.addSpacing(18)

        section = QLabel("INPUT SOURCE")
        section.setStyleSheet("font-size: 10px; color: #6b7280; letter-spacing: 2px; background: transparent;")
        sl.addWidget(section)
        sl.addSpacing(12)

        # --- Big File Button ---
        self.file_btn = QPushButton()
        self.file_btn.setFixedHeight(100)
        self.file_btn.setText("📄   Select a File")
        self.file_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
                text-align: center;
                padding: 18px;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border: 2px solid #60a5fa;
            }
        """)
        self.file_btn.clicked.connect(self.select_file)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-size: 11px; color: #6b7280; padding-left: 6px; background: transparent;")
        self.file_label.setWordWrap(True)

        sl.addWidget(self.file_btn)
        sl.addSpacing(6)
        sl.addWidget(self.file_label)
        sl.addSpacing(14)

        # --- Big Folder Button ---
        self.folder_btn = QPushButton()
        self.folder_btn.setFixedHeight(100)
        self.folder_btn.setText("📁   Select a Folder")
        self.folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
                text-align: center;
                padding: 18px;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border: 2px solid #60a5fa;
            }
        """)
        self.folder_btn.clicked.connect(self.select_folder)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("font-size: 11px; color: #6b7280; padding-left: 6px; background: transparent;")
        self.folder_label.setWordWrap(True)
        self.folder_count_label = QLabel("")
        self.folder_count_label.setStyleSheet("font-size: 11px; color: #60a5fa; padding-left: 6px; background: transparent;")

        sl.addWidget(self.folder_btn)
        sl.addSpacing(6)
        sl.addWidget(self.folder_label)
        sl.addWidget(self.folder_count_label)
        sl.addSpacing(20)
        sl.addWidget(divider())
        sl.addSpacing(18)

        # --- Scan Button ---
        self.scan_btn = QPushButton("🚀  Start Scan")
        self.scan_btn.setFixedHeight(72)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white;
                padding: 14px; border-radius: 12px;
                font-size: 18px; font-weight: bold;
                border: 2px solid transparent;
            }
            QPushButton:hover    { background-color: #1d4ed8; border: 2px solid #93c5fd; }
            QPushButton:disabled { background-color: #374151; color: #6b7280; border: none; }
        """)
        self.scan_btn.clicked.connect(self.start_scan)
        sl.addWidget(self.scan_btn)
        sl.addSpacing(10)

        # --- Clear Button ---
        self.clear_btn = QPushButton("🗑  Clear Results")
        self.clear_btn.setFixedHeight(58)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #9ca3af;
                border-radius: 10px; font-size: 14px;
                border: 2px solid #374151;
            }
            QPushButton:hover { background-color: #374151; color: white; border: 2px solid #4b5563; }
        """)
        self.clear_btn.clicked.connect(self.clear_results)
        sl.addWidget(self.clear_btn)

        sl.addSpacing(16)
        sl.addWidget(divider())

        # --- Scan Complete Indicator ---
        self.scan_complete_widget = QFrame()
        self.scan_complete_widget.setStyleSheet("QFrame { background: transparent; } QLabel { background: transparent; }")
        sc_layout = QVBoxLayout()
        sc_layout.setContentsMargins(10, 15, 10, 15)
        sc_layout.setSpacing(6)
        sc_layout.setAlignment(Qt.AlignCenter)

        sc_emoji = QLabel("✅")
        sc_emoji.setAlignment(Qt.AlignCenter)
        sc_emoji.setStyleSheet("font-size: 48px; background: transparent;")
        sc_layout.addWidget(sc_emoji)

        sc_title = QLabel("Scan Complete!")
        sc_title.setAlignment(Qt.AlignCenter)
        sc_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #10b981; background: transparent;")
        sc_layout.addWidget(sc_title)

        self.scan_complete_widget.setLayout(sc_layout)
        self.scan_complete_widget.hide()
        if hasattr(self, 'export_widget'):
            self.export_widget.hide()
        self._last_results = []
        sl.addWidget(self.scan_complete_widget)

        # --- Export Buttons (shown after scan) ---
        self.export_widget = QFrame()
        self.export_widget.setStyleSheet("QFrame { background: transparent; }")
        ex_layout = QVBoxLayout()
        ex_layout.setContentsMargins(0, 8, 0, 0)
        ex_layout.setSpacing(8)

        self.export_csv_btn = QPushButton("📄  Export as CSV")
        self.export_csv_btn.setFixedHeight(56)
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #95B9C7; color: white;
                border-radius: 10px; font-size: 14px; font-weight: bold;
                border: 2px solid #10b981;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        self.export_csv_btn.clicked.connect(self.export_csv)

        self.export_pdf_btn = QPushButton("📑  Export as PDF")
        self.export_pdf_btn.setFixedHeight(56)
        self.export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a5f; color: white;
                border-radius: 10px; font-size: 14px; font-weight: bold;
                border: 2px solid #3b82f6;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.export_pdf_btn.clicked.connect(self.export_pdf)

        ex_layout.addWidget(self.export_csv_btn)
        ex_layout.addWidget(self.export_pdf_btn)
        self.export_widget.setLayout(ex_layout)
        self.export_widget.hide()
        sl.addWidget(self.export_widget)

        # --- Animated Loader ---
        self.loader = LoaderWidget()
        sl.addWidget(self.loader)

        sl.addStretch()

        footer = QLabel("Powered by validator.py")
        footer.setStyleSheet("font-size: 10px; color: #374151; background: transparent;")
        footer.setAlignment(Qt.AlignCenter)
        sl.addWidget(footer)

        self.sidebar.setLayout(sl)

        # ================= CONTENT =================
        self.content = QFrame()
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.setStyleSheet("background-color: #f5f7fb;")

        cl = QVBoxLayout()
        cl.setContentsMargins(30, 30, 30, 30)
        cl.setSpacing(20)

        # Header
        hl = QHBoxLayout()
        hv = QVBoxLayout()
        pt = QLabel("Scan Results")
        pt.setStyleSheet("font-size: 22px; font-weight: bold; color: #1f2937;")
        ps = QLabel("Analyze file encoding across your project")
        ps.setStyleSheet("font-size: 13px; color: #6b7280;")
        hv.addWidget(pt); hv.addWidget(ps)
        hl.addLayout(hv); hl.addStretch()
        cl.addLayout(hl)

        # 5 Summary Cards
        card_row = QHBoxLayout()
        card_row.setSpacing(15)
        self.total_card   = self.create_card("Total Files",       "0", "#3b82f6", "📊")
        self.utf_card     = self.create_card("100% UTF",          "0", "#10b981", "✅")
        self.mixed_card   = self.create_card("Mostly UTF (≥90%)", "0", "#f59e0b", "🔶")
        self.non_utf_card = self.create_card("Non-UTF (<90%)",    "0", "#ef4444", "⚠️")
        self.binary_card  = self.create_card("Binary Files",      "0", "#8b5cf6", "📦")
        card_row.addWidget(self.total_card)
        card_row.addWidget(self.utf_card)
        card_row.addWidget(self.mixed_card)
        card_row.addWidget(self.non_utf_card)
        card_row.addWidget(self.binary_card)
        cl.addLayout(card_row)

        # Average UTF bar
        avg_frame = QFrame()
        avg_frame.setStyleSheet("background: white; border-radius: 12px;")
        avg_row = QHBoxLayout()
        avg_row.setContentsMargins(20, 12, 20, 12)
        avg_row.setSpacing(15)
        avg_lbl = QLabel("Average UTF Coverage across all files:")
        avg_lbl.setStyleSheet("font-size: 13px; color: #374151; font-weight: bold;")
        self.avg_bar = QProgressBar()
        self.avg_bar.setRange(0, 100)
        self.avg_bar.setValue(0)
        self.avg_bar.setFixedHeight(18)
        self.avg_bar.setTextVisible(False)
        self.avg_bar.setStyleSheet("""
            QProgressBar { background-color: #f3f4f6; border-radius: 9px; border: none; }
            QProgressBar::chunk { background-color: #10b981; border-radius: 9px; }
        """)
        self.avg_pct_label = QLabel("0%")
        self.avg_pct_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981; min-width: 45px;")
        self.avg_pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        avg_row.addWidget(avg_lbl)
        avg_row.addWidget(self.avg_bar, 1)
        avg_row.addWidget(self.avg_pct_label)
        avg_frame.setLayout(avg_row)
        cl.addWidget(avg_frame)

        # Scan spinner bar (top content area)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #e5e7eb; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 3px; }
        """)
        self.progress.hide()
        cl.addWidget(self.progress)

        # Bottom: Chart + Results
        bottom = QHBoxLayout()
        bottom.setSpacing(20)

        chart_card = QFrame()
        chart_card.setStyleSheet("background: white; border-radius: 15px;")
        chart_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chart_l = QVBoxLayout()
        chart_l.setContentsMargins(20, 20, 20, 20)
        chart_title_lbl = QLabel("Encoding Distribution")
        chart_title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937;")
        chart_l.addWidget(chart_title_lbl)
        self.figure = Figure()
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chart_l.addWidget(self.canvas)
        chart_card.setLayout(chart_l)

        results_card = QFrame()
        results_card.setStyleSheet("background: white; border-radius: 15px;")
        results_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        res_l = QVBoxLayout()
        res_l.setContentsMargins(20, 20, 20, 20)
        res_title = QLabel("File Results")
        res_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2937; margin-bottom: 10px;")
        res_l.addWidget(res_title)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #f3f4f6; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #d1d5db; border-radius: 4px; }
        """)
        self.result_container = QWidget()
        self.result_container.setStyleSheet("background: transparent;")
        self.result_layout = QVBoxLayout()
        self.result_layout.setSpacing(10)
        self.result_layout.setAlignment(Qt.AlignTop)
        self.result_container.setLayout(self.result_layout)
        self.scroll.setWidget(self.result_container)
        res_l.addWidget(self.scroll)
        results_card.setLayout(res_l)

        bottom.addWidget(chart_card, 2)
        bottom.addWidget(results_card, 3)
        cl.addLayout(bottom, 1)
        self.content.setLayout(cl)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content)

    # ---------- Card Creator ----------
    def create_card(self, title, value, color, icon=""):
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(110)
        card.setStyleSheet(f"""
            QFrame {{ background-color: {color}; border-radius: 15px; }}
            QLabel {{ color: white; background: transparent; }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setAlignment(Qt.AlignVCenter)
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        top.addWidget(icon_lbl); top.addStretch()
        layout.addLayout(top)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 32px; font-weight: bold; color: white; background: transparent;")
        layout.addWidget(val_lbl)
        ttl_lbl = QLabel(title)
        ttl_lbl.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.85); background: transparent;")
        layout.addWidget(ttl_lbl)
        card.setLayout(layout)
        card.value_label = val_lbl
        return card

    # ---------- Select File ----------
    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.selected_file   = file
            self.selected_folder = None
            self.file_label.setText(f"📄 {os.path.basename(file)}")
            self.file_label.setStyleSheet("font-size: 11px; color: #60a5fa; padding-left: 6px; background: transparent;")
            self.folder_label.setText("No folder selected")
            self.folder_label.setStyleSheet("font-size: 11px; color: #6b7280; padding-left: 6px; background: transparent;")
            self.folder_count_label.setText("")
            # Highlight selected button
            self.file_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e3a5f; color: white;
                    border-radius: 12px; font-size: 14px; font-weight: bold;
                    text-align: left; padding: 12px 16px;
                    border: 2px solid #60a5fa;
                }
                QPushButton:hover { background-color: #1e3a5f; border: 2px solid #93c5fd; }
            """)
            self.folder_btn.setStyleSheet("""
                QPushButton {
                    background-color: #374151; color: white;
                    border-radius: 12px; font-size: 14px; font-weight: bold;
                    text-align: left; padding: 12px 16px;
                    border: 2px solid transparent;
                }
                QPushButton:hover { background-color: #4b5563; border: 2px solid #60a5fa; }
            """)
            self.clear_results()

    # ---------- Select Folder ----------
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.selected_folder = folder
            self.selected_file   = None
            self.folder_label.setText(f"📁 {os.path.basename(folder)}")
            self.folder_label.setStyleSheet("font-size: 11px; color: #60a5fa; padding-left: 6px; background: transparent;")
            self.file_label.setText("No file selected")
            self.file_label.setStyleSheet("font-size: 11px; color: #6b7280; padding-left: 6px; background: transparent;")
            count = sum(len(files) for _, _, files in os.walk(folder))
            self.folder_count_label.setText(f"  {count} files found")
            # Highlight selected button
            self.folder_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e3a5f; color: white;
                    border-radius: 12px; font-size: 14px; font-weight: bold;
                    text-align: left; padding: 12px 16px;
                    border: 2px solid #60a5fa;
                }
                QPushButton:hover { background-color: #1e3a5f; border: 2px solid #93c5fd; }
            """)
            self.file_btn.setStyleSheet("""
                QPushButton {
                    background-color: #374151; color: white;
                    border-radius: 12px; font-size: 14px; font-weight: bold;
                    text-align: left; padding: 12px 16px;
                    border: 2px solid transparent;
                }
                QPushButton:hover { background-color: #4b5563; border: 2px solid #60a5fa; }
            """)
            self.clear_results()

    # ---------- Clear Results ----------
    def clear_results(self):
        while self.result_layout.count():
            child = self.result_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.total_card.value_label.setText("0")
        self.utf_card.value_label.setText("0")
        self.mixed_card.value_label.setText("0")
        self.non_utf_card.value_label.setText("0")
        self.binary_card.value_label.setText("0")
        self.avg_bar.setValue(0)
        self.avg_pct_label.setText("0%")
        self.figure.clear()
        self.canvas.draw()
        self.scan_complete_widget.hide()
        if hasattr(self, 'export_widget'):
            self.export_widget.hide()
        self._last_results = []

    # ---------- Start Scan ----------
    def start_scan(self):
        if not self.selected_file and not self.selected_folder:
            msg = QMessageBox(self)
            msg.setWindowTitle("No Input Selected")
            msg.setText("Please select a file or folder first!")
            msg.setInformativeText("Use the 'Select a File' or 'Select a Folder' button in the sidebar before starting the scan.")
            msg.setIcon(QMessageBox.Warning)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #ffffff;
                }
                QMessageBox QLabel {
                    color: #1f2937;
                    font-size: 13px;
                    font-family: Segoe UI;
                    min-width: 300px;
                }
                QPushButton {
                    background-color: #2563eb;
                    color: white;
                    padding: 8px 24px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
            """)
            msg.exec_()
            return
        self.clear_results()
        self.scan_complete_widget.hide()
        if hasattr(self, 'export_widget'):
            self.export_widget.hide()
        self._last_results = []
        self.scan_btn.setEnabled(False)
        self.progress.show()
        self.loader.start()

        # Dedicated animation thread — sleeps 1 sec then emits tick
        self._anim = AnimThread()
        self._anim.tick.connect(self.loader.next_frame)
        self._anim.start()

        self.thread = ScanThread(self.selected_file, self.selected_folder)
        self.thread.finished_signal.connect(self.display_results)
        self.thread.start()

    # ---------- Display Results ----------
    def display_results(self, data):
        self._anim.requestInterruption()
        self._anim.wait()
        self.scan_btn.setEnabled(True)
        self.progress.hide()
        self.loader.stop()

        # Show scan complete indicator with summary
        total = data["total"]
        utf   = data["utf"]
        non   = data["non_utf"]
        binary = data["binary"]
        self.scan_complete_widget.show()
        self.export_widget.show()
        self._last_results = data["results"]

        self.total_card.value_label.setText(str(data["total"]))
        self.utf_card.value_label.setText(str(data["utf"]))
        self.mixed_card.value_label.setText(str(data["mixed"]))
        self.non_utf_card.value_label.setText(str(data["non_utf"]))
        self.binary_card.value_label.setText(str(data["binary"]))

        avg = data["avg_utf_percent"]
        self.avg_bar.setValue(int(avg))
        self.avg_pct_label.setText(f"{avg}%")
        chunk_color = "#10b981" if avg >= 90 else ("#f59e0b" if avg >= 50 else "#ef4444")
        self.avg_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #f3f4f6; border-radius: 9px; border: none; }}
            QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 9px; }}
        """)
        self.avg_pct_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {chunk_color}; min-width: 45px;")

        for r in data["results"]:
            self.result_layout.addWidget(self.create_result_card(r))

        # Donut chart
        self.figure.clear()
        values = [data["utf"], data["mixed"], data["non_utf"], data["binary"]]
        labels = ["100% UTF", "Mostly UTF", "Non-UTF", "Binary"]
        colors = ["#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        filtered = [(v, l, c) for v, l, c in zip(values, labels, colors) if v > 0]
        if filtered:
            v, l, c = zip(*filtered)
            ax = self.figure.add_subplot(111)
            wedges, texts, autotexts = ax.pie(
                v, labels=l, autopct='%1.1f%%', colors=c,
                startangle=90, wedgeprops=dict(width=0.6)
            )
            for text in texts: text.set_fontsize(10)
            for at in autotexts:
                at.set_fontsize(9); at.set_color('white'); at.set_fontweight('bold')
            ax.set_title("Encoding Distribution", fontsize=13, fontweight='bold', pad=15)
        self.canvas.draw()

    # ---------- Result Card ----------
    def create_result_card(self, r):
        utf_pct     = r.get("utf_percent", 0.0)
        non_utf_pct = r.get("non_utf_percent", 0.0)
        is_binary   = r.get("is_binary", False)
        is_utf      = r.get("is_utf", False)
        is_mostly   = r.get("is_mostly_utf", False)

        if is_binary:
            border_color = "#8b5cf6"; bg_color = "#f5f3ff"
            tag_text = "📦 Binary";    tag_color = "#8b5cf6"; bar_color = "#8b5cf6"
        elif is_utf:
            border_color = "#10b981"; bg_color = "#ecfdf5"
            tag_text = "✅ 100% UTF";  tag_color = "#10b981"; bar_color = "#10b981"
        elif is_mostly:
            border_color = "#f59e0b"; bg_color = "#fffbeb"
            tag_text = "🔶 Mostly UTF"; tag_color = "#f59e0b"; bar_color = "#f59e0b"
        else:
            border_color = "#ef4444"; bg_color = "#fef2f2"
            tag_text = "⚠️ Non-UTF";   tag_color = "#ef4444"; bar_color = "#ef4444"

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background: {bg_color}; border-left: 4px solid {border_color}; border-radius: 8px; }}
            QLabel {{ background: transparent; color: #1f2937; }}
        """)

        outer = QVBoxLayout()
        outer.setContentsMargins(15, 10, 15, 10)
        outer.setSpacing(6)

        # Top row
        top_row = QHBoxLayout()
        fname = QLabel(r.get("filename", "Unknown"))
        fname.setStyleSheet("font-weight: bold; font-size: 13px;")
        tag = QLabel(tag_text)
        tag.setStyleSheet(f"""
            background-color: {tag_color}; color: white;
            border-radius: 6px; padding: 3px 10px;
            font-size: 11px; font-weight: bold;
        """)
        tag.setFixedHeight(24)
        top_row.addWidget(fname); top_row.addStretch(); top_row.addWidget(tag)
        outer.addLayout(top_row)

        if is_binary:
            info_lbl = QLabel("Binary file — encoding check not applicable")
            info_lbl.setStyleSheet("font-size: 11px; color: #8b5cf6;")
            outer.addWidget(info_lbl)
        else:
            total_chars   = r.get("total_chars", 0)
            non_utf_chars = r.get("non_utf_chars", 0)
            detected_enc  = r.get("detected_encoding", "Unknown")

            content_row = QHBoxLayout()
            content_row.setSpacing(15)

            left = QVBoxLayout()
            left.setSpacing(5)

            enc_lbl = QLabel(f"Detected encoding: {detected_enc}")
            enc_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {border_color};")
            left.addWidget(enc_lbl)

            stats = QLabel(
                f"Total chars: {total_chars:,}  •  Invalid chars: {non_utf_chars:,}  •  "
                f"UTF: {utf_pct}%  |  Non-UTF: {non_utf_pct}%"
            )
            stats.setStyleSheet("font-size: 11px; color: #6b7280;")
            left.addWidget(stats)

            bar_row = QHBoxLayout()
            bar_row.setSpacing(8)
            lbl = QLabel("UTF")
            lbl.setStyleSheet(f"font-size: 10px; color: {bar_color}; font-weight: bold; min-width: 28px;")
            bar = QProgressBar()
            bar.setRange(0, 100); bar.setValue(int(utf_pct))
            bar.setFixedHeight(10); bar.setTextVisible(False)
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: #f3f4f6; border-radius: 5px; border: none; }}
                QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 5px; }}
            """)
            pct = QLabel(f"{utf_pct}%")
            pct.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {bar_color}; min-width: 40px;")
            pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bar_row.addWidget(lbl); bar_row.addWidget(bar, 1); bar_row.addWidget(pct)
            left.addLayout(bar_row)
            content_row.addLayout(left, 1)

            # Mini pie chart for non-utf / mostly-utf
            if not is_utf:
                mini_fig = Figure(figsize=(1.5, 1.5), facecolor="none")
                mini_fig.patch.set_alpha(0)
                mini_canvas = FigureCanvas(mini_fig)
                mini_canvas.setFixedSize(110, 110)
                mini_canvas.setStyleSheet("background: transparent;")
                ax = mini_fig.add_subplot(111)
                ax.pie(
                    [utf_pct, non_utf_pct],
                    colors=[bar_color, "#e5e7eb"],
                    startangle=90,
                    wedgeprops=dict(width=0.5),
                )
                ax.text(0, 0, f"{utf_pct}%", ha="center", va="center",
                        fontsize=8, fontweight="bold", color=bar_color)
                mini_fig.tight_layout(pad=0)
                content_row.addWidget(mini_canvas)

            outer.addLayout(content_row)

        card.setLayout(outer)
        return card


    # ---------- Export CSV ----------
    def export_csv(self):
        if not self._last_results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"utf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Filename", "Status", "Detected Encoding", "Total Chars", "Invalid Chars", "UTF %", "Non-UTF %"])
                for r in self._last_results:
                    if r.get("is_binary"):
                        status = "Binary"
                    elif r.get("is_utf"):
                        status = "100% UTF"
                    elif r.get("is_mostly_utf"):
                        status = "Mostly UTF"
                    else:
                        status = "Non-UTF"
                    writer.writerow([
                        r.get("filename", ""),
                        status,
                        r.get("detected_encoding", ""),
                        r.get("total_chars", 0),
                        r.get("non_utf_chars", 0),
                        r.get("utf_percent", 0),
                        r.get("non_utf_percent", 0),
                    ])
            msg = QMessageBox(self)
            msg.setWindowTitle("Export Successful")
            msg.setText("Your CSV report is ready!")
            msg.setInformativeText(f"Saved to:\n{path}")
            msg.setIcon(QMessageBox.NoIcon)
            msg.setStyleSheet("""
                QMessageBox { background-color: #ffffff; }
                QMessageBox QLabel { color: #1f2937; font-size: 13px; font-family: Segoe UI; min-width: 320px; }
                QPushButton { background-color: #10b981; color: white; padding: 8px 24px; border-radius: 6px; font-size: 13px; font-weight: bold; min-width: 80px; }
                QPushButton:hover { background-color: #047857; }
            """)
            msg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    # ---------- Export PDF ----------
    def export_pdf(self):
        if not self._last_results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", f"utf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            doc = SimpleDocTemplate(path, pagesize=A4,
                                    leftMargin=1.5*cm, rightMargin=1.5*cm,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm)
            styles = getSampleStyleSheet()
            story = []

            # Title
            title_style = ParagraphStyle("title", fontSize=20, fontName="Helvetica-Bold",
                                         textColor=colors.HexColor("#1f2937"), spaceAfter=6, alignment=TA_CENTER)
            sub_style   = ParagraphStyle("sub", fontSize=10, fontName="Helvetica",
                                         textColor=colors.HexColor("#6b7280"), spaceAfter=20, alignment=TA_CENTER)
            story.append(Paragraph("UTF Validator Report", title_style))
            story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", sub_style))

            # Summary counts
            total   = len(self._last_results)
            utf     = sum(1 for r in self._last_results if r.get("is_utf"))
            mostly  = sum(1 for r in self._last_results if r.get("is_mostly_utf"))
            non_utf = sum(1 for r in self._last_results if not r.get("is_utf") and not r.get("is_mostly_utf") and not r.get("is_binary"))
            binary  = sum(1 for r in self._last_results if r.get("is_binary"))

            summary_data = [
                ["Total Files", "100% UTF", "Mostly UTF", "Non-UTF", "Binary"],
                [str(total), str(utf), str(mostly), str(non_utf), str(binary)],
            ]
            summary_table = Table(summary_data, colWidths=[3.5*cm]*5)
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("BACKGROUND", (0,1), (0,1),  colors.HexColor("#3b82f6")),
                ("BACKGROUND", (1,1), (1,1),  colors.HexColor("#10b981")),
                ("BACKGROUND", (2,1), (2,1),  colors.HexColor("#f59e0b")),
                ("BACKGROUND", (3,1), (3,1),  colors.HexColor("#ef4444")),
                ("BACKGROUND", (4,1), (4,1),  colors.HexColor("#8b5cf6")),
                ("TEXTCOLOR",  (0,1), (-1,1), colors.white),
                ("FONTNAME",   (0,0), (-1,-1), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 11),
                ("ALIGN",      (0,0), (-1,-1), "CENTER"),
                ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ("ROWHEIGHT",  (0,0), (-1,-1), 28),
                ("ROUNDEDCORNERS", [6]),
                ("BOX",        (0,0), (-1,-1), 0, colors.white),
                ("INNERGRID",  (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))

            # File results table
            head_style = ParagraphStyle("head", fontSize=13, fontName="Helvetica-Bold",
                                        textColor=colors.HexColor("#1f2937"), spaceAfter=10)
            story.append(Paragraph("File Results", head_style))

            table_data = [["Filename", "Status", "Encoding", "Total Chars", "Invalid", "UTF %"]]
            for r in self._last_results:
                if r.get("is_binary"):
                    status = "Binary"
                elif r.get("is_utf"):
                    status = "100% UTF"
                elif r.get("is_mostly_utf"):
                    status = "Mostly UTF"
                else:
                    status = "Non-UTF"
                table_data.append([
                    r.get("filename", "")[:35],
                    status,
                    r.get("detected_encoding", "")[:15],
                    f'{r.get("total_chars", 0):,}',
                    f'{r.get("non_utf_chars", 0):,}',
                    f'{r.get("utf_percent", 0)}%',
                ])

            col_widths = [6*cm, 2.5*cm, 3*cm, 2.5*cm, 2*cm, 1.8*cm]
            file_table = Table(table_data, colWidths=col_widths, repeatRows=1)

            row_styles = [
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("ALIGN",      (0,0), (-1,-1), "CENTER"),
                ("ALIGN",      (0,1), (0,-1), "LEFT"),
                ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
                ("ROWHEIGHT",  (0,0), (-1,-1), 20),
                ("INNERGRID",  (0,0), (-1,-1), 0.3, colors.HexColor("#e5e7eb")),
                ("BOX",        (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
            ]
            # Color status column rows
            status_colors = {"100% UTF": "#d1fae5", "Mostly UTF": "#fef3c7", "Non-UTF": "#fee2e2", "Binary": "#ede9fe"}
            for i, r in enumerate(self._last_results, start=1):
                if r.get("is_binary"):    s = "Binary"
                elif r.get("is_utf"):     s = "100% UTF"
                elif r.get("is_mostly_utf"): s = "Mostly UTF"
                else: s = "Non-UTF"
                bg = status_colors.get(s, "#ffffff")
                row_styles.append(("BACKGROUND", (1,i), (1,i), colors.HexColor(bg)))
                row_styles.append(("BACKGROUND", (0,i), (0,i), colors.white if i%2==0 else colors.HexColor("#f9fafb")))

            file_table.setStyle(TableStyle(row_styles))
            story.append(file_table)

            doc.build(story)

            msg = QMessageBox(self)
            msg.setWindowTitle("Export Successful")
            msg.setText("Your PDF report is ready!")
            msg.setInformativeText(f"Saved to:\n{path}")
            msg.setIcon(QMessageBox.NoIcon)
            msg.setStyleSheet("""
                QMessageBox { background-color: #ffffff; }
                QMessageBox QLabel { color: #1f2937; font-size: 13px; font-family: Segoe UI; min-width: 320px; }
                QPushButton { background-color: #2563eb; color: white; padding: 8px 24px; border-radius: 6px; font-size: 13px; font-weight: bold; min-width: 80px; }
                QPushButton:hover { background-color: #1d4ed8; }
            """)
            msg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    window = UTFValidatorApp()
    window.showMaximized()
    sys.exit(app.exec_())
    
"""     ("🕵️", "Detecting encodings..."),
        ("🔬", "Checking UTF validity..."),
        ("🚀", "Almost there..."),
        ("✨", "Wrapping things up..."),
        ("🎯", "Finalizing results...")"""