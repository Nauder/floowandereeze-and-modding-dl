from UnityPy.enums import TextureFormat
from typing_extensions import override

from database.models import FieldModel
from database.objects import session
from services.unity_service import UnityService
from unity.unity_utils import prepare_environment
from UnityPy import load as unity_load

from util.constants import APP_CONFIG
from util.enums import FieldCoordinates
from util.image_utils import convert_image, paste_scaled_image


class FieldService(UnityService):

    def __init__(self):
        super().__init__("fields")

    @override
    def replace_bundle(self) -> None:

        if not self.bundle or not self.image_path:
            return

        f_path = prepare_environment(False, self.bundle)
        env = unity_load(f_path)

        for obj in env.objects:
            if obj.type.name == "Texture2D":

                data = obj.read()

                img = convert_image(self.image_path)

                data.m_Width, data.m_Height = img.size

                data.set_image(
                    img=img,
                    target_format=TextureFormat.RGBA32,
                    mipmap_count=APP_CONFIG.mipmap_count,
                )

                data.save()
                break

        with open(f_path, "wb") as f:
            f.write(env.file.save(packer=APP_CONFIG.packer))
