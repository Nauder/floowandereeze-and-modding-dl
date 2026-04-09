from PIL import Image
from UnityPy.enums import TextureFormat
from typing_extensions import override

from database.models import CharacterModel
from database.objects import session
from services.unity_service import UnityService
from unity.unity_utils import prepare_environment
from UnityPy import load as unity_load

from util.constants import APP_CONFIG
from util.image_utils import convert_image


class CharacterService(UnityService):

    def __init__(self):
        super().__init__("characters")

    @override
    def replace_bundle(self) -> None:
        if not self.bundle or not self.image_path:
            return

        f_path = prepare_environment(False, self.bundle)
        env = unity_load(f_path)

        new_img = convert_image(self.image_path)

        orig_size = None

        for obj in env.objects:
            if obj.type.name == "Texture2D":
                data = obj.read()

                # Resize to original texture dimensions to keep sprite vertex data valid
                orig_size = (data.m_Width, data.m_Height)
                if new_img.size != orig_size:
                    new_img = new_img.resize(orig_size, Image.Resampling.LANCZOS)

                data.set_image(
                    img=new_img,
                    target_format=TextureFormat.RGBA32,
                    mipmap_count=APP_CONFIG.mipmap_count,
                )
                data.save()
                break

        # Fix sprite render data so it samples the full texture
        if orig_size:
            for obj in env.objects:
                if obj.type.name == "Sprite":
                    try:
                        sprite_data = obj.read()
                        if hasattr(sprite_data, "m_RD"):
                            rd = sprite_data.m_RD
                            if hasattr(rd, "textureRect"):
                                rd.textureRect.x = 0
                                rd.textureRect.y = 0
                                rd.textureRect.width = orig_size[0]
                                rd.textureRect.height = orig_size[1]
                            if hasattr(rd, "textureRectOffset"):
                                rd.textureRectOffset.X = 0
                                rd.textureRectOffset.Y = 0
                        if hasattr(sprite_data, "m_Rect"):
                            sprite_data.m_Rect.x = 0
                            sprite_data.m_Rect.y = 0
                            sprite_data.m_Rect.width = orig_size[0]
                            sprite_data.m_Rect.height = orig_size[1]
                        sprite_data.save()
                    except Exception as e:
                        print(f"Error processing sprite: {e}")
                        continue

        with open(f_path, "wb") as f:
            f.write(env.file.save(packer=APP_CONFIG.packer))

    def get_series_list(self) -> list[str]:
        """Get unique list of character series for filtering."""
        series_list = session.query(CharacterModel.series).distinct().all()
        return [series[0] for series in series_list if series[0]]
