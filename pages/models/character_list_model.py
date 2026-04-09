from textwrap import shorten
from threading import Thread

from PySide6.QtGui import Qt
from typing_extensions import override

from database.models import CharacterModel
from database.objects import session
from pages.models.asset_list_model import AssetListModel
from unity.unity_utils import fetch_bundle_thumb


class CharacterListModel(AssetListModel):

    def __init__(self, characters=None):
        super().__init__(characters or [], CharacterModel)
        self.show_favorites = False
        self.series_filter = ""

    @override
    def refresh(self):
        query = session.query(self.db_model)

        if self.series_filter != "":
            query = query.filter(self.db_model.series == self.series_filter)

        if self.show_favorites:
            query = query.filter(self.db_model.favorite == True)

        self.assets = query.order_by(self.db_model.series).all()

        refresh_threads = [
            Thread(target=lambda character=char: self._refresh_character(character))
            for char in self.assets if char.icon
        ]

        for thread in refresh_threads:
            thread.start()
        for thread in refresh_threads:
            thread.join()

    def _refresh_character(self, character: CharacterModel):
        character.thumb = fetch_bundle_thumb(character.icon, (128, 128))

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return ""

        if role == Qt.DecorationRole:
            return self.assets[index.row()].thumb
