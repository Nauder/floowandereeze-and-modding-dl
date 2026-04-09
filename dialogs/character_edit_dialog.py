"""Character editing dialog module."""

from typing import Optional, List, Tuple
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QSplitter,
    QFrame,
    QFileDialog,
    QMessageBox,
)
from pyqttoast import ToastPreset

from database.models import CharacterModel
from database.objects import session
from services.character_service import CharacterService
from unity.unity_utils import fetch_bundle_thumb
from util.constants import IMAGE_FILTER, APP_CONFIG
from util.ui_util import show_toast
from util.enums import CharaAssetType


class CharacterEditDialog(QDialog):
    """Modal dialog for editing character assets."""

    def __init__(self, character: CharacterModel, parent=None):
        super().__init__(parent)
        self.character = character
        self.service = CharacterService()
        self.selected_asset_bundle: Optional[str] = None
        self.selected_asset_type: Optional[CharaAssetType] = None

        self.setWindowTitle(f"Edit Character - {character.series}")
        self.setModal(True)
        self.resize(800, 600)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._populate_asset_list()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the dialog UI layout."""
        layout = QVBoxLayout(self)

        # Header with character icon and title
        header_layout = QHBoxLayout()

        # Character icon
        self.character_icon = QLabel()
        self.character_icon.setFixedSize(64, 64)
        self.character_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.character.icon:
            icon = fetch_bundle_thumb(self.character.icon, None)
            if icon and icon.availableSizes():
                raw = icon.pixmap(icon.availableSizes()[0])
                self.character_icon.setPixmap(
                    raw.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
        header_layout.addWidget(self.character_icon)

        # Title
        title_label = QLabel(f"Editing {self.character.series} Character")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Asset list with filter
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)

        # Filter combo box
        filter_label = QLabel("Filter by type:")
        left_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Assets", "all")
        self.filter_combo.addItem("Duel Assets", "duel")
        self.filter_combo.addItem("Dialog Assets", "dialog")
        self.filter_combo.addItem("Miscellaneous", "misc")
        left_layout.addWidget(self.filter_combo)

        # Asset list
        assets_label = QLabel("Character Assets:")
        left_layout.addWidget(assets_label)

        self.asset_list = QListWidget()
        self.asset_list.setIconSize(QSize(64, 64))
        left_layout.addWidget(self.asset_list)

        splitter.addWidget(left_frame)

        # Right side - Preview and image selection
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)

        # Current asset preview
        preview_label = QLabel("Asset Preview:")
        right_layout.addWidget(preview_label)

        self.current_preview = QLabel()
        self.current_preview.setFixedSize(256, 256)
        self.current_preview.setStyleSheet("border: 1px solid gray;")
        self.current_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_preview.setText("Select an asset to preview")
        right_layout.addWidget(self.current_preview)

        # Image selection
        image_label = QLabel("Replacement Image:")
        right_layout.addWidget(image_label)

        image_layout = QHBoxLayout()
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setReadOnly(True)
        self.image_path_edit.setPlaceholderText("No image selected")
        image_layout.addWidget(self.image_path_edit)

        self.select_image_btn = QPushButton("Select Image")
        image_layout.addWidget(self.select_image_btn)

        right_layout.addLayout(image_layout)

        # New image preview
        new_preview_label = QLabel("New Image Preview:")
        right_layout.addWidget(new_preview_label)

        self.new_preview = QLabel()
        self.new_preview.setFixedSize(256, 256)
        self.new_preview.setStyleSheet("border: 1px solid gray;")
        self.new_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_preview.setText("No image selected")
        right_layout.addWidget(self.new_preview)

        right_layout.addStretch()

        splitter.addWidget(right_frame)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.extract_btn = QPushButton("Extract Asset")
        self.extract_btn.setEnabled(False)
        button_layout.addWidget(self.extract_btn)

        self.replace_btn = QPushButton("Replace Asset")
        self.replace_btn.setEnabled(False)
        button_layout.addWidget(self.replace_btn)

        self.restore_btn = QPushButton("Restore Asset")
        self.restore_btn.setEnabled(False)
        button_layout.addWidget(self.restore_btn)

        close_btn = QPushButton("Close")
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Connect close button
        close_btn.clicked.connect(self.accept)

    def _connect_signals(self):
        """Connect UI signals to their handlers."""
        self.filter_combo.currentTextChanged.connect(self._filter_assets)
        self.asset_list.itemClicked.connect(self._on_asset_selected)
        self.select_image_btn.clicked.connect(self._select_image)
        self.extract_btn.clicked.connect(self._extract_asset)
        self.replace_btn.clicked.connect(self._replace_asset)
        self.restore_btn.clicked.connect(self._restore_asset)

    def _populate_asset_list(self):
        """Populate the asset list with character's available assets."""
        self.asset_list.clear()

        # Get all asset types and their corresponding bundles
        self.asset_data: List[Tuple[CharaAssetType, str, str]] = []

        for asset_type in CharaAssetType:
            bundle = self.character.get_asset_bundle(asset_type)
            if bundle:  # Only add assets that have bundles
                self.asset_data.append(
                    (asset_type, bundle, self._get_asset_display_name(asset_type))
                )

        self._filter_assets()

    def _get_asset_display_name(self, asset_type: CharaAssetType) -> str:
        """Get a user-friendly display name for an asset type."""
        name_map = {
            CharaAssetType.ICON: "Character Icon",
            CharaAssetType.SELECT: "Selection Screen",
            CharaAssetType.WORLD: "World Map",
            CharaAssetType.EVENT: "Event Screen",
            CharaAssetType.CUTIN: "Cut-in Animation",
            CharaAssetType.VICTORY: "Victory Screen",
            CharaAssetType.DEFEAT: "Defeat Screen",
            CharaAssetType.VERSUS: "Versus Screen",
            CharaAssetType.SELECTED_LEGACY: "Selected (Legacy)",
            CharaAssetType.SELECTED_NEW: "Selected (New)",
            CharaAssetType.HOME_VICTORY: "Home Victory",
            CharaAssetType.HOME_SPECIAL: "Home Special",
            CharaAssetType.NAME_BIG: "Name (Large)",
            CharaAssetType.NAME_SMALL: "Name (Small)",
        }

        # Handle duel assets
        if asset_type.name.startswith("DUEL_"):
            duel_num = asset_type.name.split("_")[1]
            return f"Duel Animation {duel_num}"

        # Handle dialog assets
        if asset_type.name.startswith("DIALOG_"):
            dialog_num = asset_type.name.split("_")[1]
            return f"Dialog Expression {dialog_num}"

        return name_map.get(asset_type, asset_type.name.replace("_", " ").title())

    def _get_asset_category(self, asset_type: CharaAssetType) -> str:
        """Get the category of an asset type for filtering."""
        if asset_type.name.startswith("DUEL_"):
            return "duel"
        elif asset_type.name.startswith("DIALOG_"):
            return "dialog"
        else:
            return "misc"

    def _filter_assets(self):
        """Filter assets based on the selected filter."""
        self.asset_list.clear()
        filter_type = self.filter_combo.currentData()

        for asset_type, bundle, display_name in self.asset_data:
            if (
                filter_type == "all"
                or self._get_asset_category(asset_type) == filter_type
            ):
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, (asset_type, bundle))

                # Set thumbnail if available
                try:
                    item.setIcon(fetch_bundle_thumb(bundle, None))
                except Exception:
                    item.setIcon(QIcon())

                self.asset_list.addItem(item)

    def _on_asset_selected(self, item: QListWidgetItem):
        """Handle asset selection from the list."""
        asset_type, bundle = item.data(Qt.ItemDataRole.UserRole)
        self.selected_asset_type = asset_type
        self.selected_asset_bundle = bundle

        # Update preview
        try:
            icon = fetch_bundle_thumb(bundle, None)
            if icon and icon.availableSizes():
                raw = icon.pixmap(icon.availableSizes()[0])
                self.current_preview.setPixmap(
                    raw.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
        except Exception:
            self.current_preview.setText("Preview not available")

        # Enable buttons
        self.extract_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)

        # Enable replace button only if image is selected
        self._update_replace_button_state()

        # Set service bundle
        self.service.bundle = bundle

    def _select_image(self):
        """Open file dialog to select replacement image."""
        file, _ = QFileDialog.getOpenFileUrl(
            self, "Select Replacement Image", "", IMAGE_FILTER
        )

        if file and file.url():
            local_file = file.toLocalFile()
            self.image_path_edit.setText(local_file)
            self.service.image_path = local_file

            # Show preview of new image
            pixmap = QPixmap(local_file)
            self.new_preview.setPixmap(
                pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

            self._update_replace_button_state()

    def _update_replace_button_state(self):
        """Update the replace button enabled state."""
        has_image = bool(self.service.image_path)
        has_asset = bool(self.selected_asset_bundle)
        self.replace_btn.setEnabled(has_image and has_asset)

    def _extract_asset(self):
        """Extract the selected asset to the characters folder."""
        if not self.selected_asset_bundle:
            return

        try:
            self.service.extract_texture(self.selected_asset_bundle)
            show_toast(
                self,
                "Character Extraction",
                'Asset extracted to the "characters" folder',
                ToastPreset.SUCCESS_DARK,
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Extraction Error", f"Failed to extract asset: {str(e)}"
            )

    def _replace_asset(self):
        """Replace the selected asset with the chosen image."""
        if not self.selected_asset_bundle or not self.service.image_path:
            return

        try:
            # Create backup if enabled and not already backed up
            if APP_CONFIG.create_backup and not self.character.has_backup:
                self.service.create_backup(self.selected_asset_bundle)
                self.character.has_backup = True
                session.commit()

            # Replace the asset
            self.service.replace_bundle()

            # Update the preview to show the new image
            try:
                icon = fetch_bundle_thumb(self.selected_asset_bundle, None)
                if icon and icon.availableSizes():
                    raw = icon.pixmap(icon.availableSizes()[0])
                    self.current_preview.setPixmap(
                        raw.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
            except Exception:
                pass

            show_toast(
                self,
                "Character Replacement",
                "Asset replacement successful",
                ToastPreset.SUCCESS_DARK,
            )

        except Exception as e:
            QMessageBox.warning(
                self, "Replacement Error", f"Failed to replace asset: {str(e)}"
            )
            print(str(e))

    def _restore_asset(self):
        """Restore the selected asset from backup."""
        if not self.selected_asset_bundle:
            return

        try:
            if self.service.restore_asset():
                # Update the preview
                try:
                    icon = fetch_bundle_thumb(self.selected_asset_bundle, None)
                    if icon and icon.availableSizes():
                        raw = icon.pixmap(icon.availableSizes()[0])
                        self.current_preview.setPixmap(
                            raw.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        )
                except Exception:
                    pass

                show_toast(
                    self,
                    "Character Restore",
                    "Asset restored successfully",
                    ToastPreset.SUCCESS_DARK,
                )
            else:
                show_toast(
                    self,
                    "Character Restore",
                    "Asset backup not found",
                    ToastPreset.WARNING_DARK,
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Restore Error", f"Failed to restore asset: {str(e)}"
            )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag and drop of image files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if (
                    url.toLocalFile()
                    .lower()
                    .endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event of an image file."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                self.image_path_edit.setText(file_path)
                self.service.image_path = file_path

                # Show preview of new image
                pixmap = QPixmap(file_path)
                self.new_preview.setPixmap(
                    pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )

                self._update_replace_button_state()
                break
