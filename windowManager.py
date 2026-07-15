# windowManager.py
import glob
import os
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QTabWidget, QWidget
)
from configManager import loadConfig, saveConfig
from kdlmUtils import getKdlMeta, readKdlmArchive, writeKdlmArchive


class ProjectCard(QFrame):
    doubleClicked = pyqtSignal(str)
    actionTriggered = pyqtSignal(str, str)

    def __init__(self, projectPath, isNew=False, parent=None):
        super().__init__(parent)
        self.projectPath = projectPath
        self.setFixedSize(240, 200)

        self.isMissing = not os.path.exists(projectPath)

        # Safe read if file is available
        if not self.isMissing:
            _, duration, xmlName, kdenliveVer, _ = getKdlMeta(projectPath)
        else:
            duration, xmlName, kdenliveVer = "00:00:00", os.path.basename(projectPath), "N/A"

        self.kdlmPath = projectPath.rsplit('.', 1)[0] + ".kdlm"
        metaDict, thumbnailBytes = readKdlmArchive(self.kdlmPath)

        self.displayName = xmlName
        self.notes = ""
        self.tags = []
        self.hasCustomThumbnail = False

        if metaDict:
            self.displayName = metaDict.get("projectName", xmlName)
            self.notes = metaDict.get("notes", "")
            self.tags = metaDict.get("tags", [])
            self.hasCustomThumbnail = metaDict.get("customThumbnail", False)

        cardTitle = f"[NEW] {self.displayName}" if isNew else self.displayName
        if self.isMissing:
            cardTitle = f"[MISSING] {self.displayName}"

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ProjectCard {
                border: 1px solid #444;
                border-radius: 6px;
                background-color: #1e1e1e;
            }
            ProjectCard:hover {
                border: 1px solid #3daee9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.thumbPlaceholder = QLabel()
        self.thumbPlaceholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.isMissing:
            self.thumbPlaceholder.setText("FILE NOT FOUND")
            self.thumbPlaceholder.setStyleSheet("background-color: #3a1a1a; color: #ff5555; border-radius: 4px; font-weight: bold; min-height: 100px;")
        elif self.hasCustomThumbnail and thumbnailBytes:
            qImage = QImage.fromData(thumbnailBytes)
            pixmap = QPixmap.fromImage(qImage)
            scaledPixmap = pixmap.scaled(224, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumbPlaceholder.setPixmap(scaledPixmap)
            self.thumbPlaceholder.setStyleSheet("background-color: #000; border-radius: 4px;")
        else:
            self.thumbPlaceholder.setText("[No Thumbnail]")
            self.thumbPlaceholder.setStyleSheet("background-color: #2a2a2a; color: #888; border-radius: 4px; min-height: 100px;")

        layout.addWidget(self.thumbPlaceholder, stretch=1)

        infoLayout = QHBoxLayout()
        self.titleLabel = QLabel(cardTitle)
        if self.isMissing:
            self.titleLabel.setStyleSheet("font-weight: bold; font-size: 11px; color: #ff5555;")
        elif isNew:
            self.titleLabel.setStyleSheet("font-weight: bold; font-size: 11px; color: #3daee9;")
        else:
            self.titleLabel.setStyleSheet("font-weight: bold; font-size: 11px; color: #fff;")

        self.titleLabel.setToolTip(self.displayName)

        durationLabel = QLabel(duration)
        durationLabel.setStyleSheet("color: #bbb; font-size: 10px;")

        infoLayout.addWidget(self.titleLabel)
        infoLayout.addStretch()
        infoLayout.addWidget(durationLabel)
        layout.addLayout(infoLayout)

        notesSnippet = self.notes.strip().replace("\n", " ")
        if len(notesSnippet) > 35:
            notesSnippet = notesSnippet[:32] + "..."

        self.notesLabel = QLabel(notesSnippet if notesSnippet else "No notes added")
        self.notesLabel.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        layout.addWidget(self.notesLabel)

        tagsLayout = QHBoxLayout()
        tagsLayout.setSpacing(4)
        for tag in self.tags[:3]:
            tagBadge = QLabel(f" {tag} ")
            tagBadge.setStyleSheet("""
                background-color: #2a2a2a;
                color: #aaa;
                border-radius: 3px;
                font-size: 9px;
                font-weight: bold;
            """)
            tagsLayout.addWidget(tagBadge)
        tagsLayout.addStretch()
        layout.addLayout(tagsLayout)

        bottomRowLayout = QHBoxLayout()

        verLabel = QLabel(f"v{kdenliveVer}")
        verLabel.setStyleSheet("color: #555; font-size: 9px;")
        bottomRowLayout.addWidget(verLabel)
        bottomRowLayout.addStretch()

        self.burgerButton = QPushButton("•••")
        self.burgerButton.setFixedSize(28, 16)
        self.burgerButton.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888;
                border: none;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #3daee9;
            }
        """)
        self.burgerButton.clicked.connect(self.showCardMenuFromBurger)
        bottomRowLayout.addWidget(self.burgerButton)

        layout.addLayout(bottomRowLayout)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMissing:
            self.doubleClicked.emit(self.projectPath)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.showCardMenu(event.globalPos())

    def showCardMenuFromBurger(self):
        buttonBottomLeft = self.burgerButton.mapToGlobal(self.burgerButton.rect().bottomLeft())
        self.showCardMenu(buttonBottomLeft)

    def showCardMenu(self, globalPos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #3daee9;
            }
            QMenu::item:disabled {
                color: #555;
            }
        """)

        openAction = menu.addAction("Open Project")
        if self.isMissing:
            openAction.setEnabled(False)

        editNotesAction = menu.addAction("Edit Project")
        if self.isMissing:
            editNotesAction.setEnabled(False)

        restoreBackupAction = menu.addAction("Restore Backup...")
        if self.isMissing:
            restoreBackupAction.setEnabled(False)

        renameAction = menu.addAction("Rename Project")
        if self.isMissing:
            renameAction.setEnabled(False)

        deleteAction = menu.addAction("Delete Project")

        action = menu.exec(globalPos)

        if action == openAction:
            self.actionTriggered.emit("open", self.projectPath)
        elif action == editNotesAction:
            self.handleEditProject()
        elif action == restoreBackupAction:
            self.handleRestoreBackup()
        elif action == renameAction:
            self.actionTriggered.emit("rename", self.projectPath)
        elif action == deleteAction:
            self.actionTriggered.emit("delete", self.projectPath)

    def handleEditProject(self):
        dialog = EditProjectModal(self.projectPath, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.actionTriggered.emit("refresh", self.projectPath)

    def handleRestoreBackup(self):
        dialog = BackupRestoreDialog(self.projectPath, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.actionTriggered.emit("refresh", self.projectPath)


class BackupRestoreDialog(QDialog):
    def __init__(self, projectPath, parent=None):
        super().__init__(parent)
        self.projectPath = projectPath
        self.setWindowTitle("Restore Project Backup")
        self.resize(500, 350)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #fff; }
            QLabel { color: #fff; font-weight: bold; }
            QListWidget { background-color: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #333; }
            QListWidget::item:selected { background-color: #3daee9; color: white; }
            QPushButton { background-color: #2a2a2a; color: white; border: 1px solid #444; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #3daee9; border-color: #3daee9; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Available Kdenlive System Backups:"))
        self.backupList = QListWidget()
        layout.addWidget(self.backupList)

        backupDir = os.path.expanduser("~/.local/share/kdenlive/.backup/")
        baseName = os.path.basename(projectPath).rsplit('.', 1)[0]

        backupsFound = []

        if os.path.exists(backupDir):
            for file in os.listdir(backupDir):
                if file.startswith(baseName) and file.endswith(".kdenlive"):
                    fullPath = os.path.join(backupDir, file)
                    backupsFound.append(fullPath)

        backupsFound.sort(key=os.path.getmtime, reverse=True)

        for backupPath in backupsFound:
            filename = os.path.basename(backupPath)
            parts = filename.rsplit('-', 5)
            if len(parts) >= 6:
                timestampStr = f"{parts[-5]}-{parts[-4]}-{parts[-3]} {parts[-2]}:{parts[-1].replace('.kdenlive', '')}"
                displayName = f"Backup from {timestampStr}\n({filename})"
            else:
                displayName = filename

            item = QListWidgetItem(displayName)
            item.setData(Qt.ItemDataRole.UserRole, backupPath)
            self.backupList.addItem(item)

        if not backupsFound:
            noItem = QListWidgetItem("No backups found for this project in ~/.local/share/kdenlive/.backup/")
            self.backupList.addItem(noItem)
            self.backupList.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancelBtn = QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.reject)
        buttons.addWidget(self.cancelBtn)

        self.restoreBtn = QPushButton("Restore Selected Backup")
        self.restoreBtn.clicked.connect(self.handleRestore)
        if not backupsFound:
            self.restoreBtn.setEnabled(False)
        buttons.addWidget(self.restoreBtn)

        layout.addLayout(buttons)

    def handleRestore(self):
        selectedItem = self.backupList.currentItem()
        if not selectedItem:
            return

        backupPath = selectedItem.data(Qt.ItemDataRole.UserRole)
        if not backupPath or not os.path.exists(backupPath):
            return

        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            "Are you sure you want to overwrite your active project file with this backup?\n\nThis will replace your current project file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(backupPath, "r", encoding="utf-8") as bf:
                    data = bf.read()
                with open(self.projectPath, "w", encoding="utf-8") as pf:
                    pf.write(data)

                QMessageBox.information(self, "Success", "Backup restored successfully!")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Restore Error", f"Could not restore backup file:\n{e}")

class EditProjectModal(QDialog):
    def __init__(self, projectPath, parent=None):
        super().__init__(parent)
        self.projectPath = projectPath
        self.kdlmPath = projectPath.rsplit('.', 1)[0] + ".kdlm"

        self.setWindowTitle("Edit Project")
        self.resize(450, 480)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #fff; }
            QLabel { color: #fff; font-weight: bold; font-size: 11px; }
            QLineEdit, QTextEdit { background-color: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 4px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 1px solid #444; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #3daee9; border-color: #3daee9; }
            QPushButton:disabled { background-color: #1a1a1a; color: #555; border-color: #333; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        _, _, xmlName, _, _ = getKdlMeta(projectPath)
        self.metadataDict, self.thumbnailBytes = readKdlmArchive(self.kdlmPath)

        if not self.metadataDict:
            self.metadataDict = {
                "projectName": xmlName,
                "notes": "",
                "tags": [],
                "customThumbnail": False,
                "thumbnailType": None
            }

        layout.addWidget(QLabel("Project Title Display Name:"))
        self.titleInput = QLineEdit()
        self.titleInput.setText(self.metadataDict.get("projectName", xmlName))
        layout.addWidget(self.titleInput)

        layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tagsInput = QLineEdit()
        loadedTags = self.metadataDict.get("tags", [])
        self.tagsInput.setText(", ".join(loadedTags))
        layout.addWidget(self.tagsInput)

        layout.addWidget(QLabel("Thumbnail status:"))
        thumbControlLayout = QHBoxLayout()

        self.thumbnailPathLabel = QLineEdit()
        self.thumbnailPathLabel.setReadOnly(True)
        self.thumbnailPathLabel.setPlaceholderText("No thumbnail set")

        hasThumbnail = bool(self.thumbnailBytes) or self.metadataDict.get("customThumbnail", False)
        thumbType = self.metadataDict.get("thumbnailType", None)

        if hasThumbnail:
            if thumbType == "custom":
                self.thumbnailPathLabel.setText("Active (Custom)")
            elif thumbType == "auto":
                self.thumbnailPathLabel.setText("Active (Auto)")
            else:
                self.thumbnailPathLabel.setText("Active (Custom)")

        self.browseThumbButton = QPushButton("Browse...")
        self.browseThumbButton.clicked.connect(self.handleBrowseThumbnail)

        self.resetThumbButton = QPushButton("Reset")
        self.resetThumbButton.setEnabled(hasThumbnail)
        self.resetThumbButton.clicked.connect(self.handleResetThumbnail)

        thumbControlLayout.addWidget(self.thumbnailPathLabel)
        thumbControlLayout.addWidget(self.browseThumbButton)
        thumbControlLayout.addWidget(self.resetThumbButton)
        layout.addLayout(thumbControlLayout)

        layout.addWidget(QLabel("Custom Notes / Description:"))
        self.notesInput = QTextEdit()
        self.notesInput.setText(self.metadataDict.get("notes", ""))
        layout.addWidget(self.notesInput)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(self.cancelButton)

        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.handleSave)
        buttonLayout.addWidget(self.saveButton)

        layout.addLayout(buttonLayout)

    def handleBrowseThumbnail(self):
        imagePath, _ = QFileDialog.getOpenFileName(
            self, "Select Custom Thumbnail Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if imagePath:
            self.thumbnailPathLabel.setText(imagePath)
            self.selectedImagePath = imagePath
            self.resetThumbButton.setEnabled(True)

    def handleResetThumbnail(self):
        if hasattr(self, "selectedImagePath"):
            delattr(self, "selectedImagePath")

        self.thumbnailBytes = None
        self.metadataDict["customThumbnail"] = False
        self.metadataDict["thumbnailType"] = None

        self.thumbnailPathLabel.setText("")
        self.thumbnailPathLabel.setPlaceholderText("No thumbnail set")
        self.resetThumbButton.setEnabled(False)

    def handleSave(self):
        self.metadataDict["projectName"] = self.titleInput.text().strip()
        self.metadataDict["notes"] = self.notesInput.toPlainText().strip()

        rawTags = self.tagsInput.text().split(",")
        cleanedTags = [t.strip() for t in rawTags if t.strip()]
        self.metadataDict["tags"] = cleanedTags

        if hasattr(self, "selectedImagePath") and os.path.exists(self.selectedImagePath):
            try:
                with open(self.selectedImagePath, "rb") as imageFile:
                    self.thumbnailBytes = imageFile.read()
                self.metadataDict["customThumbnail"] = True
                self.metadataDict["thumbnailType"] = "custom"
            except Exception as e:
                QMessageBox.warning(self, "Image Error", f"Could not read selected image file:\n{e}")

        success = writeKdlmArchive(self.kdlmPath, self.metadataDict, self.thumbnailBytes)
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save companion .kdlm archive.")

class SettingsModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("kdlManager Settings")
        self.resize(550, 480)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #fff; }
            QLabel { color: #fff; font-weight: bold; }
            QCheckBox { color: #fff; }
            QListWidget { background-color: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 1px solid #444; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #3daee9; border-color: #3daee9; }
            QTabWidget::pane { border: 1px solid #444; background: #1e1e1e; border-radius: 4px; }
            QTabBar::tab { background: #2a2a2a; color: #aaa; padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #3daee9; color: white; font-weight: bold; }
            QTableWidget { background-color: #2a2a2a; color: #fff; gridline-color: #444; border: 1px solid #444; border-radius: 4px; }
            QHeaderView::section { background-color: #1e1e1e; color: #fff; padding: 4px; border: 1px solid #444; font-weight: bold; }
        """)

        mainLayout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        mainLayout.addWidget(self.tabs)

        self.tabStandard = QWidget()
        tab1Layout = QVBoxLayout(self.tabStandard)
        tab1Layout.setSpacing(12)

        optionsLayout = QVBoxLayout()
        optionsLayout.setSpacing(8)

        self.reopenCheckbox = QCheckBox("Reopen kdlManager after Kdenlive closes")
        self.reopenCheckbox.stateChanged.connect(self.handleReopenToggle)
        optionsLayout.addWidget(self.reopenCheckbox)

        self.launchButtonCheckbox = QCheckBox("Show 'Launch Kdenlive' Button")
        self.launchButtonCheckbox.stateChanged.connect(self.handleLaunchButtonToggle)
        optionsLayout.addWidget(self.launchButtonCheckbox)

        self.watchFoldersCheckbox = QCheckBox("Auto-Scan Folders in Background (Every 5s)")
        self.watchFoldersCheckbox.stateChanged.connect(self.handleWatchFoldersToggle)
        optionsLayout.addWidget(self.watchFoldersCheckbox)

        tab1Layout.addLayout(optionsLayout)

        tab1Layout.addWidget(QLabel("Indexed Folders:"))
        self.folderList = QListWidget()
        tab1Layout.addWidget(self.folderList)

        folderActionsLayout = QHBoxLayout()
        self.removeFolderButton = QPushButton("Remove Selected Folder")
        self.removeFolderButton.clicked.connect(self.handleRemoveFolder)
        folderActionsLayout.addWidget(self.removeFolderButton)
        folderActionsLayout.addStretch()
        tab1Layout.addLayout(folderActionsLayout)

        self.tabs.addTab(self.tabStandard, "General Settings")

        self.tabExperimental = QWidget()
        tab2Layout = QVBoxLayout(self.tabExperimental)
        tab2Layout.setSpacing(10)

        tab2Layout.addWidget(QLabel("🔬 Advanced Experimental Flags"))
        infoText = QLabel("Note: Experimental settings may alter project archives or background processing cycles. They will not corrupt your Project")
        infoText.setStyleSheet("color: #ffa500; font-size: 10px; font-style: italic;")
        tab2Layout.addWidget(infoText)

        self.experimentalTable = QTableWidget()
        self.experimentalTable.setColumnCount(3)
        self.experimentalTable.setHorizontalHeaderLabels(["Setting", "Value", "Default"])

        self.experimentalTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.experimentalTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.experimentalTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.experimentalTable.horizontalHeader().setMinimumSectionSize(80)

        self.experimentalTable.verticalHeader().setVisible(False)
        self.experimentalTable.setRowCount(1)

        itemSetting = QTableWidgetItem("autoProjectThumbnails")
        itemSetting.setFlags(itemSetting.flags() ^ Qt.ItemFlag.ItemIsEditable) # Read-only
        itemSetting.setToolTip("Searches system backup folders to extract & embed missing project thumbnails.")
        self.experimentalTable.setItem(0, 0, itemSetting)

        self.valDropdown = QComboBox()
        self.valDropdown.addItems(["false", "true"])
        self.valDropdown.setStyleSheet("background-color: #1e1e1e; color: #fff; border: none; padding: 2px;")
        self.valDropdown.currentTextChanged.connect(self.handleAutoThumbnailsChanged)
        self.experimentalTable.setCellWidget(0, 1, self.valDropdown)

        itemDefault = QTableWidgetItem("true")
        itemDefault.setFlags(itemDefault.flags() ^ Qt.ItemFlag.ItemIsEditable)
        itemDefault.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.experimentalTable.setItem(0, 2, itemDefault)

        tab2Layout.addWidget(self.experimentalTable)
        self.tabs.addTab(self.tabExperimental, "Experimental")

        bottomLayout = QHBoxLayout()
        bottomLayout.addStretch()
        self.closeButton = QPushButton("Close")
        self.closeButton.clicked.connect(self.accept)
        bottomLayout.addWidget(self.closeButton)
        mainLayout.addLayout(bottomLayout)

        self.loadCurrentSettings()

    def loadCurrentSettings(self):
        config = loadConfig()
        self.reopenCheckbox.setChecked(config.get("reopenOnClose", True))
        self.launchButtonCheckbox.setChecked(config.get("showLaunchButton", True))
        self.watchFoldersCheckbox.setChecked(config.get("watchFolders", True))

        isAutoThumbEnabled = config.get("autoProjectThumbnails", False)
        self.valDropdown.setCurrentText("true" if isAutoThumbEnabled else "false")

        self.folderList.clear()
        for folder in config.get("indexedFolders", []):
            self.folderList.addItem(folder)

    def handleReopenToggle(self, state):
        config = loadConfig()
        config["reopenOnClose"] = (state == Qt.CheckState.Checked.value)
        saveConfig(config)

    def handleLaunchButtonToggle(self, state):
        config = loadConfig()
        config["showLaunchButton"] = (state == Qt.CheckState.Checked.value)
        saveConfig(config)

    def handleWatchFoldersToggle(self, state):
        config = loadConfig()
        config["watchFolders"] = (state == Qt.CheckState.Checked.value)
        saveConfig(config)

    def handleAutoThumbnailsChanged(self, text):
        config = loadConfig()
        config["autoProjectThumbnails"] = (text == "true")
        saveConfig(config)

    def handleRemoveFolder(self):
        currentItem = self.folderList.currentItem()
        if not currentItem:
            return

        folderPath = currentItem.text()
        reply = QMessageBox.question(
            self, "Remove Index Path", f"Stop indexing\n{folderPath}\n?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            config = loadConfig()
            if folderPath in config["indexedFolders"]:
                config["indexedFolders"].remove(folderPath)
                saveConfig(config)
                self.loadCurrentSettings()
