from database.models import FieldModel
from pages.models.named_asset_list_model import NamedAssetListModel


class FieldListModel(NamedAssetListModel):
    def __init__(self, fields=None):
        super().__init__(fields, FieldModel, (256, 128))

    @property
    def fields(self):
        return self.assets
