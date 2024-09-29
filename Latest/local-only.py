import sys
import os
import tarfile
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QFileDialog,
                             QTextEdit, QMessageBox, QMainWindow, QStatusBar)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QPalette, QColor

class BackupThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, agent_folder, prompt_folder, output_folder, snapshot_folder):
        QThread.__init__(self)
        self.agent_folder = agent_folder
        self.prompt_folder = prompt_folder
        self.output_folder = output_folder
        self.snapshot_folder = snapshot_folder

    def run(self):
        try:
            # Create snapshot folder
            snapshot_name = datetime.now().strftime("%d%m%y_vault_snapshot")
            snapshot_path = os.path.join(self.snapshot_folder, snapshot_name)
            os.makedirs(snapshot_path, exist_ok=True)
            self.update_signal.emit(f"Created snapshot folder: {snapshot_path}")

            # Create archives
            self.create_archive(self.agent_folder, os.path.join(snapshot_path, "agents.tar.gz"), "agents")
            self.create_archive(self.prompt_folder, os.path.join(snapshot_path, "prompts.tar.gz"), "prompts")
            self.create_archive(self.output_folder, os.path.join(snapshot_path, "outputs.tar.gz"), "outputs")

            self.update_signal.emit("Snapshot creation completed successfully!")
            self.finished_signal.emit(True)
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False)

    def create_archive(self, source_folder, archive_name, archive_type):
        self.update_signal.emit(f"Creating {archive_type} archive...")
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(source_folder, arcname=os.path.basename(source_folder))
        self.update_signal.emit(f"{archive_type.capitalize()} archive created: {archive_name}")

class LLMVaultBackupUtility(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_config()

    def initUI(self):
        self.setWindowTitle('LLM Vault Backup Utility')
        self.setGeometry(100, 100, 600, 400)

        # Set the color scheme
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Folder selection
        self.create_folder_input(layout, "Agent Folder:", "agent_folder")
        self.create_folder_input(layout, "Prompt Folder:", "prompt_folder")
        self.create_folder_input(layout, "Output Folder:", "output_folder")
        self.create_folder_input(layout, "Snapshot Folder:", "snapshot_folder")

        # Create snapshot and Save Config buttons
        button_layout = QHBoxLayout()
        self.create_snapshot_btn = QPushButton('Create Snapshot')
        self.create_snapshot_btn.clicked.connect(self.create_snapshot)
        self.create_snapshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.create_snapshot_btn)

        self.save_config_btn = QPushButton('Save Config')
        self.save_config_btn.clicked.connect(self.save_config)
        self.save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007B9A;
            }
        """)
        button_layout.addWidget(self.save_config_btn)

        layout.addLayout(button_layout)

        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(QLabel("Process Output:"))
        layout.addWidget(self.terminal_output)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def create_folder_input(self, layout, label_text, attribute_name):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit()
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        setattr(self, attribute_name, line_edit)
        h_layout.addWidget(line_edit)
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(lambda: self.browse_folder(attribute_name))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        h_layout.addWidget(browse_btn)
        layout.addLayout(h_layout)

    def browse_folder(self, attribute_name):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            getattr(self, attribute_name).setText(folder)

    def create_snapshot(self):
        agent_folder = self.agent_folder.text()
        prompt_folder = self.prompt_folder.text()
        output_folder = self.output_folder.text()
        snapshot_folder = self.snapshot_folder.text()

        if not all([agent_folder, prompt_folder, output_folder, snapshot_folder]):
            QMessageBox.warning(self, "Input Error", "All folder paths must be specified.")
            return

        self.backup_thread = BackupThread(agent_folder, prompt_folder, output_folder, snapshot_folder)
        self.backup_thread.update_signal.connect(self.update_terminal)
        self.backup_thread.finished_signal.connect(self.backup_finished)
        self.backup_thread.start()
        self.create_snapshot_btn.setEnabled(False)

    def update_terminal(self, message):
        self.terminal_output.append(message)
        self.statusBar.showMessage(message, 3000)

    def backup_finished(self, success):
        self.create_snapshot_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", "Snapshot created successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to create snapshot. Check the process output for details.")

    def save_config(self):
        config = {
            'agent_folder': self.agent_folder.text(),
            'prompt_folder': self.prompt_folder.text(),
            'output_folder': self.output_folder.text(),
            'snapshot_folder': self.snapshot_folder.text()
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)
        self.statusBar.showMessage("Configuration saved successfully", 3000)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            self.agent_folder.setText(config.get('agent_folder', ''))
            self.prompt_folder.setText(config.get('prompt_folder', ''))
            self.output_folder.setText(config.get('output_folder', ''))
            self.snapshot_folder.setText(config.get('snapshot_folder', ''))
            self.statusBar.showMessage("Configuration loaded successfully", 3000)
        except FileNotFoundError:
            self.statusBar.showMessage("No saved configuration found", 3000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    ex = LLMVaultBackupUtility()
    ex.show()
    sys.exit(app.exec_())