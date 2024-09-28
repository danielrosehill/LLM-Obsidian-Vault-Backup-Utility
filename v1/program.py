import sys
import os
import tarfile
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QFileDialog, 
                             QTextEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal

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

class LLMVaultBackupUtility(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('LLM Vault Backup Utility')
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        # Folder selection
        self.create_folder_input(layout, "Agent Folder:", "agent_folder")
        self.create_folder_input(layout, "Prompt Folder:", "prompt_folder")
        self.create_folder_input(layout, "Output Folder:", "output_folder")
        self.create_folder_input(layout, "Snapshot Folder:", "snapshot_folder")

        # Create snapshot button
        self.create_snapshot_btn = QPushButton('Create Snapshot')
        self.create_snapshot_btn.clicked.connect(self.create_snapshot)
        layout.addWidget(self.create_snapshot_btn)

        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        layout.addWidget(QLabel("Process Output:"))
        layout.addWidget(self.terminal_output)

        self.setLayout(layout)

    def create_folder_input(self, layout, label_text, attribute_name):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit()
        setattr(self, attribute_name, line_edit)
        h_layout.addWidget(line_edit)
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(lambda: self.browse_folder(attribute_name))
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

    def backup_finished(self, success):
        self.create_snapshot_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", "Snapshot created successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to create snapshot. Check the process output for details.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LLMVaultBackupUtility()
    ex.show()
    sys.exit(app.exec_())