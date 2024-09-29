import sys
import os
import tarfile
import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QFileDialog,
                             QTextEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal
import b2sdk.v2 as b2

def get_secrets_file_path():
    home_dir = Path.home()
    secrets_dir = home_dir / "secrets"
    secrets_file = secrets_dir / "obsidian-to-b2.json"
    return secrets_file

class BackupThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, agent_folder, prompt_folder, output_folder, snapshot_folder, b2_key_id, b2_key_secret, b2_bucket_name, b2_folder):
        QThread.__init__(self)
        self.agent_folder = agent_folder
        self.prompt_folder = prompt_folder
        self.output_folder = output_folder
        self.snapshot_folder = snapshot_folder
        self.b2_key_id = b2_key_id
        self.b2_key_secret = b2_key_secret
        self.b2_bucket_name = b2_bucket_name
        self.b2_folder = b2_folder

    def run(self):
        try:
            # Create snapshot folder with a unique name
            snapshot_name = datetime.now().strftime("%d%m%y_%H%M%S_vault_snapshot")
            snapshot_path = os.path.join(self.snapshot_folder, snapshot_name)
            os.makedirs(snapshot_path, exist_ok=True)
            self.update_signal.emit(f"Created snapshot folder: {snapshot_path}")

            # Create archives
            archives = [
                self.create_archive(self.agent_folder, os.path.join(snapshot_path, "agents.tar.gz"), "agents"),
                self.create_archive(self.prompt_folder, os.path.join(snapshot_path, "prompts.tar.gz"), "prompts"),
                self.create_archive(self.output_folder, os.path.join(snapshot_path, "outputs.tar.gz"), "outputs")
            ]

            # Upload archives to B2
            self.upload_to_b2(archives, snapshot_name)
            self.update_signal.emit("Snapshot creation and upload completed successfully!")
            self.finished_signal.emit(True)
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False)

    def create_archive(self, source_folder, archive_name, archive_type):
        self.update_signal.emit(f"Creating {archive_type} archive...")
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(source_folder, arcname=os.path.basename(source_folder))
        self.update_signal.emit(f"{archive_type.capitalize()} archive created: {archive_name}")
        return archive_name

    def upload_to_b2(self, archives, snapshot_name):
        self.update_signal.emit("Initializing B2 upload...")
        info = b2.InMemoryAccountInfo()
        b2_api = b2.B2Api(info)
        try:
            b2_api.authorize_account("production", self.b2_key_id, self.b2_key_secret)
        except b2.exception.B2Error as e:
            self.update_signal.emit(f"B2 Authentication Error: {str(e)}")
            raise
        try:
            bucket = b2_api.get_bucket_by_name(self.b2_bucket_name)
        except b2.exception.B2Error as e:
            self.update_signal.emit(f"B2 Bucket Error: {str(e)}")
            raise
        for archive in archives:
            file_name = os.path.basename(archive)
            b2_file_name = f"{self.b2_folder}/{snapshot_name}/{file_name}".lstrip('/')
            self.update_signal.emit(f"Uploading {file_name} to B2...")
            try:
                bucket.upload_local_file(
                    local_file=archive,
                    file_name=b2_file_name,
                    content_type="application/gzip"
                )
                self.update_signal.emit(f"Uploaded {file_name} to B2")
            except b2.exception.B2Error as e:
                self.update_signal.emit(f"B2 Upload Error: {str(e)}")
                raise

class LLMVaultBackupUtility(QWidget):
    def __init__(self):
        super().__init__()
        self.secrets_file = get_secrets_file_path()
        self.load_secrets()
        self.initUI()

    def load_secrets(self):
        if self.secrets_file.exists():
            with open(self.secrets_file, 'r') as f:
                self.secrets = json.load(f)
        else:
            self.secrets = {}

    def save_secrets(self):
        self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.secrets_file, 'w') as f:
            json.dump(self.secrets, f, indent=4)

    def initUI(self):
        self.setWindowTitle('LLM Vault Backup Utility')
        self.setGeometry(100, 100, 600, 600)
        layout = QVBoxLayout()

        # Local Folder Configuration
        layout.addWidget(QLabel("Local Folder Configuration"))
        self.create_folder_input(layout, "Agent Folder:", "agent_folder",
                                 "The path to your local folder in which LLM agent configurations are stored")
        self.create_folder_input(layout, "Prompt Folder:", "prompt_folder",
                                 "The path to your local folder in which your prompts are stored")
        self.create_folder_input(layout, "Output Folder:", "output_folder",
                                 "The path to the folder in which outputs are stored in your Obsidian LLM vault")
        self.create_folder_input(layout, "Snapshot Folder:", "snapshot_folder",
                                 "The local folder where snapshots will be temporarily stored before uploading")

        # B2 Bucket Configuration
        layout.addWidget(QLabel("B2 Bucket Configuration"))
        self.create_text_input(layout, "B2 Key ID:", "b2_key_id",
                               "Your Backblaze B2 Key ID")
        self.create_text_input(layout, "B2 Key Secret:", "b2_key_secret",
                               "Your Backblaze B2 Key Secret")
        self.create_text_input(layout, "B2 Bucket Name:", "b2_bucket_name",
                               "The name of your Backblaze B2 bucket")
        self.create_text_input(layout, "B2 Folder:", "b2_folder",
                               "Folder to store snapshots in B2 (relative to bucket base, will be created if it doesn't exist)")

        # Save Credentials button
        self.save_credentials_btn = QPushButton('Save Credentials')
        self.save_credentials_btn.clicked.connect(self.save_credentials)
        layout.addWidget(self.save_credentials_btn)

        # Create snapshot button
        self.create_snapshot_btn = QPushButton('Create Snapshot and Upload to B2')
        self.create_snapshot_btn.clicked.connect(self.create_snapshot)
        layout.addWidget(self.create_snapshot_btn)

        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        layout.addWidget(QLabel("Process Output:"))
        layout.addWidget(self.terminal_output)

        self.setLayout(layout)

    def create_folder_input(self, layout, label_text, attribute_name, helper_text):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit(self.secrets.get(attribute_name, ''))
        setattr(self, attribute_name, line_edit)
        h_layout.addWidget(line_edit)
        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(lambda: self.browse_folder(attribute_name))
        h_layout.addWidget(browse_btn)
        layout.addLayout(h_layout)
        self.add_helper_text(layout, helper_text)

    def create_text_input(self, layout, label_text, attribute_name, helper_text):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit(self.secrets.get(attribute_name, ''))
        setattr(self, attribute_name, line_edit)
        h_layout.addWidget(line_edit)
        layout.addLayout(h_layout)
        self.add_helper_text(layout, helper_text)

    def add_helper_text(self, layout, helper_text):
        helper_label = QLabel(helper_text)
        helper_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(helper_label)

    def browse_folder(self, attribute_name):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            getattr(self, attribute_name).setText(folder)
            self.secrets[attribute_name] = folder
            self.save_secrets()

    def save_credentials(self):
        self.update_secrets()
        self.save_secrets()
        QMessageBox.information(self, "Success", "Credentials saved successfully!")

    def update_secrets(self):
        self.secrets.update({
            'agent_folder': self.agent_folder.text(),
            'prompt_folder': self.prompt_folder.text(),
            'output_folder': self.output_folder.text(),
            'snapshot_folder': self.snapshot_folder.text(),
            'b2_key_id': self.b2_key_id.text(),
            'b2_key_secret': self.b2_key_secret.text(),
            'b2_bucket_name': self.b2_bucket_name.text(),
            'b2_folder': self.b2_folder.text()
        })

    def create_snapshot(self):
        if not all([self.agent_folder.text(), self.prompt_folder.text(), self.output_folder.text(),
                    self.snapshot_folder.text(), self.b2_key_id.text(), self.b2_key_secret.text(),
                    self.b2_bucket_name.text()]):
            QMessageBox.warning(self, "Input Error", "All fields must be filled except B2 Folder (which is optional).")
            return

        self.update_secrets()
        self.save_secrets()

        self.backup_thread = BackupThread(
            self.secrets['agent_folder'],
            self.secrets['prompt_folder'],
            self.secrets['output_folder'],
            self.secrets['snapshot_folder'],
            self.secrets['b2_key_id'],
            self.secrets['b2_key_secret'],
            self.secrets['b2_bucket_name'],
            self.secrets['b2_folder']
        )
        self.backup_thread.update_signal.connect(self.update_terminal)
        self.backup_thread.finished_signal.connect(self.backup_finished)
        self.backup_thread.start()
        self.create_snapshot_btn.setEnabled(False)

    def update_terminal(self, message):
        self.terminal_output.append(message)

    def backup_finished(self, success):
        self.create_snapshot_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", "Snapshot created and uploaded to B2 successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to create snapshot or upload to B2. Check the process output for details.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LLMVaultBackupUtility()
    ex.show()
    sys.exit(app.exec_())