from database.models import SleeveModel
from pages.models.named_asset_list_model import NamedAssetListModel


class SleeveListModel(NamedAssetListModel):
    def __init__(self, sleeves=None):
        super().__init__(sleeves, SleeveModel, (128, 181))
