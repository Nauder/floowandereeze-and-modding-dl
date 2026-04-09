"""Character management page module."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from pyqttoast import ToastPreset

from database.models import CharacterModel
from database.objects import session
from dialogs.character_edit_dialog import CharacterEditDialog
from pages.models.character_list_model import CharacterListModel
from pages.ui.character import Ui_Character
from services.character_service import CharacterService
from util.ui_util import show_toast


class Character(QWidget, Ui_Character):
    """Character management page widget."""

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.service = CharacterService()
        self.model = CharacterListModel()
        self.charactersView.setModel(self.model)
        self.selected: Optional[CharacterModel] = None

        self._setup_series_filter()
        self._connect_callbacks()

    def _setup_series_filter(self):
        """Setup the series filter combobox."""
        series_list = self.service.get_series_list()
        self.seriesComboBox.addItem("All Series", "")
        for series in sorted(series_list):
            self.seriesComboBox.addItem(series, series)

    def _connect_callbacks(self):
        """Connect UI signals to their handlers."""
        self.charactersView.doubleClicked.connect(self._on_character_double_clicked)
        self.clearFilterButton.clicked.connect(self._clear_filters)
        self.favorite.stateChanged.connect(self._toggle_favorite)
        self.favorites.stateChanged.connect(self._toggle_favorites_filter)
        self.seriesComboBox.currentTextChanged.connect(self._filter_by_series)

    def _toggle_favorite(self, state):
        """Toggle favorite status of selected character."""
        if self.selected and self.selected.favorite != (
            state == Qt.CheckState.Checked.value
        ):
            self.selected.favorite = state == Qt.CheckState.Checked.value
            session.commit()
            show_toast(
                self,
                "Favorite",
                "Character favorite status updated",
                ToastPreset.SUCCESS_DARK,
            )

    def _toggle_favorites_filter(self, state):
        """Toggle the favorites filter."""
        self.model.show_favorites = state == Qt.CheckState.Checked.value
        if self.model.show_favorites:
            self.model.refresh()
            self.model.layoutChanged.emit()

    def _filter_by_series(self):
        """Filter characters by selected series."""
        selected_series = self.seriesComboBox.currentData()
        self.model.series_filter = selected_series or ""
        self.model.refresh()
        self.model.layoutChanged.emit()

    def _clear_filters(self):
        """Clear all filters and reset the view."""
        self.seriesComboBox.setCurrentIndex(0)
        self.favorites.setChecked(False)
        self.model.filter = ""
        self.model.series_filter = ""
        self.model.show_favorites = False
        self.model.refresh()
        self.model.layoutChanged.emit()

    def _on_character_double_clicked(self, index):
        """Handle double-click on character to open edit dialog."""
        character = self.model.assets[index.row()]
        self.selected = character

        # Update favorite checkbox
        self.favorite.setChecked(character.favorite)

        # Open the character edit dialog
        dialog = CharacterEditDialog(character, self)
        dialog.exec()

        # Refresh the model after dialog closes to update any changes
        self.model.refresh()
