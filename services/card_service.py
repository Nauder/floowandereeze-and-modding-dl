from UnityPy.enums import TextureFormat
from typing_extensions import override

from database.models import CardModel
from database.objects import session
from services.unity_service import UnityService
from unity.unity_utils import prepare_environment
from UnityPy import load as unity_load

from util.constants import APP_CONFIG
from util.enums import CardArtCoordinates
from util.image_utils import convert_image


class CardService(UnityService):

    def __init__(self):
        super().__init__("cards")
        self.unity_file: bool = False

    @override
    def replace_bundle(self) -> None:

        if not self.bundle or not self.image_path:
            return

        card: CardModel = (
            session.query(CardModel)
            .filter(CardModel.large_bundle == self.bundle)
            .first()
        )

        if card:
            self.unity_file = card.unity_file

        for bundle, size in zip(
            [card.small_bundle, card.medium_bundle, card.large_bundle],
            [
                CardArtCoordinates.SMALL,
                CardArtCoordinates.MEDIUM,
                CardArtCoordinates.LARGE,
            ],
        ):

            f_path = prepare_environment(self.unity_file, bundle)
            env = unity_load(f_path)

            for obj in env.objects:
                if obj.type.name == "Texture2D":

                    data = obj.read()

                    # Get the original image from the bundle
                    original_img = data.image.copy()

                    # Load and resize the new image to fit the coordinates area
                    new_img = convert_image(self.image_path)
                    coord_width = size.value[2] - size.value[0]  # right - left
                    coord_height = size.value[3] - size.value[1]  # bottom - top
                    new_img = new_img.resize((coord_width, coord_height))

                    # Paste the new image onto the original at the specified coordinates
                    original_img.paste(new_img, (size.value[0], size.value[1]))

                    data.set_image(
                        img=original_img,
                        target_format=TextureFormat.RGBA32,
                        mipmap_count=APP_CONFIG.mipmap_count,
                    )

                    data.save()
                    break

            with open(f_path, "wb") as f:
                f.write(env.file.save(packer=APP_CONFIG.packer))

    def get_names(self) -> list[str]:
        return [card.name for card in session.query(CardModel).all()]
