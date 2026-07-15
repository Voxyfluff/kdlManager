# main.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QScrollArea, QVBoxLayout, QHBoxLayout, QPushButton, QMenu, QFileDialog, QStyle,
    QDialog, QInputDialog, QMessageBox, QLineEdit, QComboBox
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QProcess, QSize, QTimer
from configManager import loadConfig, saveConfig
from windowManager import ProjectCard, SettingsModal
from kdlmUtils import scanIndexedFolders, readKdlmArchive, writeKdlmArchive

class KdlManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("kdlManager")
        self.resize(900, 650)
        self.setStyleSheet("background-color: #121212;")

        self.kdenliveProcess = None
        self.newlyAddedPaths = set()
        self.lastScannedPaths = []

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setContentsMargins(15, 15, 15, 15)

        topBarLayout = QHBoxLayout()

        self.settingsButton = QPushButton()
        self.settingsButton.setFixedSize(36, 36)
        systemGearIcon = QIcon.fromTheme("preferences-system")
        if systemGearIcon.isNull():
            systemGearIcon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
        self.settingsButton.setIcon(systemGearIcon)
        self.settingsButton.setIconSize(QSize(18, 18))
        self.settingsButton.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; border: 1px solid #444; border-radius: 4px; }
            QPushButton:hover { background-color: #3daee9; border-color: #3daee9; }
        """)
        self.settingsButton.clicked.connect(self.openSettings)
        topBarLayout.addWidget(self.settingsButton)

        self.addButton = QPushButton()
        self.addButton.setFixedSize(36, 36)
        systemAddIcon = QIcon.fromTheme("list-add")
        if systemAddIcon.isNull():
            systemAddIcon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        self.addButton.setIcon(systemAddIcon)
        self.addButton.setIconSize(QSize(18, 18))
        self.addButton.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; border: 1px solid #444; border-radius: 4px; }
            QPushButton:hover { background-color: #3daee9; border-color: #3daee9; }
        """)
        self.addButton.clicked.connect(self.showAddMenu)
        topBarLayout.addWidget(self.addButton)

        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search projects, notes...")
        self.searchBar.setFixedHeight(36)
        self.searchBar.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #444;
                border-radius: 4px;
                padding-left: 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3daee9;
            }
        """)
        self.searchBar.textChanged.connect(self.populateProjects)
        topBarLayout.addWidget(self.searchBar, stretch=1)

        self.tagFilterDropdown = QComboBox()
        self.tagFilterDropdown.setFixedHeight(36)
        self.tagFilterDropdown.setMinimumWidth(120)
        self.tagFilterDropdown.setStyleSheet("""
            QComboBox {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #444;
                border-radius: 4px;
                padding-left: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #fff;
                selection-background-color: #3daee9;
            }
        """)
        self.tagFilterDropdown.currentTextChanged.connect(self.populateProjects)
        topBarLayout.addWidget(self.tagFilterDropdown)

        mainLayout.addLayout(topBarLayout)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        mainLayout.addWidget(scrollArea, stretch=1)

        gridContainer = QWidget()
        gridContainer.setStyleSheet("background-color: transparent;")
        self.gridLayout = QGridLayout(gridContainer)
        self.gridLayout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.gridLayout.setSpacing(15)
        scrollArea.setWidget(gridContainer)

        bottomLayout = QHBoxLayout()
        bottomLayout.addStretch()

        self.launchKdenliveButton = QPushButton("Launch Kdenlive")
        self.launchKdenliveButton.setStyleSheet("""
            QPushButton { background-color: #3daee9; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2a9cd6; }
        """)
        self.launchKdenliveButton.clicked.connect(self.handleLaunchOnly)
        bottomLayout.addWidget(self.launchKdenliveButton)

        mainLayout.addLayout(bottomLayout)

        self.scannerTimer = QTimer(self)
        self.scannerTimer.timeout.connect(self.handleBackgroundScan)
        self.scannerTimer.start(5000)

        self.populateProjects(rebuildDropdown=True)

    def openSettings(self):
        modal = SettingsModal(self)
        if modal.exec() == QDialog.DialogCode.Accepted:
            self.populateProjects(rebuildDropdown=True)

    def showAddMenu(self):
        addMenu = QMenu(self)
        addMenu.setStyleSheet("""
            QMenu { background-color: #1e1e1e; color: #fff; border: 1px solid #444; }
            QMenu::item:selected { background-color: #3daee9; }
        """)
        addProjectAction = addMenu.addAction("Add kdenlive project")
        addFolderAction = addMenu.addAction("Add folder to index")

        action = addMenu.exec(self.addButton.mapToGlobal(self.addButton.rect().bottomLeft()))
        if action == addProjectAction:
            self.handleAddProject()
        elif action == addFolderAction:
            self.handleAddFolder()

    def handleAddProject(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Select Kdenlive Project File", "", "Kdenlive Project Files (*.kdenlive)"
        )
        if filePath:
            config = loadConfig()
            if filePath not in config["projectPaths"]:
                config["projectPaths"].append(filePath)
                saveConfig(config)
                self.newlyAddedPaths.add(filePath)
                self.populateProjects(rebuildDropdown=True)

    def handleAddFolder(self):
        folderPath = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folderPath:
            config = loadConfig()
            if folderPath not in config["indexedFolders"]:
                config["indexedFolders"].append(folderPath)
                saveConfig(config)
                self.populateProjects(rebuildDropdown=True)

    def handleBackgroundScan(self):
        config = loadConfig()
        if not config.get("watchFolders", True):
            return

        indexedFolders = config.get("indexedFolders", [])
        currentScanned = scanIndexedFolders(indexedFolders)

        if set(currentScanned) != set(self.lastScannedPaths):
            self.lastScannedPaths = currentScanned
            self.populateProjects(rebuildDropdown=True)

    def populateProjects(self, rebuildDropdown=False):
        searchText = self.searchBar.text().lower()
        selectedTag = self.tagFilterDropdown.currentText()

        config = loadConfig()
        showLaunch = config.get("showLaunchButton", True)
        autoExtractThumbs = config.get("autoProjectThumbnails", False)
        self.launchKdenliveButton.setVisible(showLaunch)

        manualPaths = config.get("projectPaths", [])
        indexedFolders = config.get("indexedFolders", [])
        scannedPaths = scanIndexedFolders(indexedFolders)
        self.lastScannedPaths = scannedPaths
        launchHistory = config.get("launchHistory", [])

        allPaths = list(manualPaths)
        for path in scannedPaths:
            if path not in allPaths:
                allPaths.append(path)

        if autoExtractThumbs:
            for path in allPaths:
                kdlmPath = path.rsplit('.', 1)[0] + ".kdlm"
                meta, thumb = readKdlmArchive(kdlmPath)

                if not thumb or not (meta and meta.get("customThumbnail", False)):
                    from kdlmUtils import extractVideoFrame

                    extracted_bytes = extractVideoFrame(path)

                    if extracted_bytes:
                        if not meta:
                            meta = {
                                "projectName": os.path.basename(path).rsplit('.', 1)[0],
                                "notes": "",
                                "tags": [],
                                "customThumbnail": True,
                                "thumbnailType": "auto"
                            }
                        else:
                            meta["customThumbnail"] = True
                            meta["thumbnailType"] = "auto"

                        writeKdlmArchive(kdlmPath, meta, extracted_bytes)

        if rebuildDropdown:
            allAvailableTags = set()
            for path in allPaths:
                kdlmPath = path.rsplit('.', 1)[0] + ".kdlm"
                meta, _ = readKdlmArchive(kdlmPath)
                if meta and "tags" in meta:
                    allAvailableTags.update(meta["tags"])

            self.tagFilterDropdown.blockSignals(True)
            self.tagFilterDropdown.clear()
            self.tagFilterDropdown.addItem("All Tags")
            for t in sorted(allAvailableTags):
                self.tagFilterDropdown.addItem(t)
            if selectedTag and selectedTag in allAvailableTags:
                self.tagFilterDropdown.setCurrentText(selectedTag)
            else:
                selectedTag = "All Tags"
            self.tagFilterDropdown.blockSignals(False)

        for i in reversed(range(self.gridLayout.count())):
            widget = self.gridLayout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        launched = [path for path in launchHistory if path in allPaths]
        launched.reverse()

        unlaunched = []
        for path in reversed(manualPaths):
            if path not in launched and path in allPaths:
                unlaunched.append(path)
        for path in scannedPaths:
            if path not in launched and path not in unlaunched and path in allPaths:
                unlaunched.append(path)

        sortedPaths = launched + unlaunched

        filteredPaths = []
        for path in sortedPaths:
            baseName = os.path.basename(path).lower()
            kdlmPath = path.rsplit('.', 1)[0] + ".kdlm"
            meta, _ = readKdlmArchive(kdlmPath)

            pName = meta.get("projectName", "").lower() if meta else baseName
            pNotes = meta.get("notes", "").lower() if meta else ""
            pTags = meta.get("tags", []) if meta else []

            if selectedTag != "All Tags" and selectedTag not in pTags:
                continue

            if searchText and (searchText not in pName and searchText not in pNotes):
                continue

            filteredPaths.append(path)

        maxCols = 3
        for index, path in enumerate(filteredPaths):
            isNew = path in self.newlyAddedPaths
            card = ProjectCard(path, isNew=isNew)
            card.doubleClicked.connect(self.launchProject)
            card.actionTriggered.connect(self.handleCardAction)
            row = index // maxCols
            col = index % maxCols
            self.gridLayout.addWidget(card, row, col)

    def handleCardAction(self, actionName, projectPath):
        if actionName == "open":
            self.launchProject(projectPath)
        elif actionName == "refresh":
            self.populateProjects(rebuildDropdown=True)
        elif actionName == "rename":
            self.handleRenameProject(projectPath)
        elif actionName == "delete":
            self.handleDeleteProject(projectPath)

    def handleRenameProject(self, projectPath):
        baseName = os.path.basename(projectPath).rsplit('.', 1)[0]
        newName, ok = QInputDialog.getText(
            self, "Rename Project", "Enter new name for the project files:", text=baseName
        )
        if not ok or not newName.strip():
            return

        newName = newName.strip()
        dirPath = os.path.dirname(projectPath)

        newXmlPath = os.path.join(dirPath, f"{newName}.kdenlive")
        oldKdlmPath = projectPath.rsplit('.', 1)[0] + ".kdlm"
        newKdlmPath = os.path.join(dirPath, f"{newName}.kdlm")

        try:
            os.rename(projectPath, newXmlPath)
            if os.path.exists(oldKdlmPath):
                os.rename(oldKdlmPath, newKdlmPath)

            config = loadConfig()
            if projectPath in config["projectPaths"]:
                idx = config["projectPaths"].index(projectPath)
                config["projectPaths"][idx] = newXmlPath
            if projectPath in config["launchHistory"]:
                idx = config["launchHistory"].index(projectPath)
                config["launchHistory"][idx] = newXmlPath
            saveConfig(config)

            if projectPath in self.newlyAddedPaths:
                self.newlyAddedPaths.remove(projectPath)
                self.newlyAddedPaths.add(newXmlPath)

            self.populateProjects(rebuildDropdown=True)
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed", f"Could not rename project files:\n{e}")

    def handleDeleteProject(self, projectPath):
        baseName = os.path.basename(projectPath).rsplit('.', 1)[0]

        existsOnDisk = os.path.exists(projectPath)
        msgPrompt = (
            f"Are you sure you want to permanently delete project files for '{baseName}'?\n\nThis will remove both the .kdenlive and .kdlm files from disk."
            if existsOnDisk else
            f"This project is missing from your machine.\n\nWould you like to remove the dead reference '{baseName}' from kdlManager's dashboard?"
        )

        reply = QMessageBox.question(
            self, "Confirm Delete/Remove", msgPrompt, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            kdlmPath = projectPath.rsplit('.', 1)[0] + ".kdlm"
            try:
                if existsOnDisk:
                    if os.path.exists(projectPath):
                        os.remove(projectPath)
                    if os.path.exists(kdlmPath):
                        os.remove(kdlmPath)

                config = loadConfig()
                if projectPath in config["projectPaths"]:
                    config["projectPaths"].remove(projectPath)
                if projectPath in config["launchHistory"]:
                    config["launchHistory"].remove(projectPath)
                saveConfig(config)

                if projectPath in self.newlyAddedPaths:
                    self.newlyAddedPaths.remove(projectPath)

                self.populateProjects(rebuildDropdown=True)
            except Exception as e:
                QMessageBox.critical(self, "Removal Failed", f"Could not clear references:\n{e}")

    def launchProject(self, projectPath=None):
        config = loadConfig()
        reopenOnClose = config.get("reopenOnClose", True)

        if projectPath:
            history = config.get("launchHistory", [])
            if projectPath in history:
                history.remove(projectPath)
            history.append(projectPath)
            config["launchHistory"] = history
            saveConfig(config)

        self.kdenliveProcess = QProcess(self)

        if reopenOnClose:
            self.hide()
            self.kdenliveProcess.finished.connect(self.handleProcessFinished)
            arguments = [projectPath] if projectPath else []
            self.kdenliveProcess.start("kdenlive", arguments)
        else:
            arguments = [projectPath] if projectPath else []
            self.kdenliveProcess.startDetached("kdenlive", arguments)
            QApplication.quit()

    def handleProcessFinished(self, exitCode, exitStatus):
        self.show()
        self.populateProjects(rebuildDropdown=True)

    def handleLaunchOnly(self):
        self.launchProject()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KdlManagerApp()
    window.show()
    sys.exit(app.exec())
