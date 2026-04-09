import struct

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

        # Fix sprite render data so it samples the full texture with a rectangular mesh
        if orig_size:
            w, h = orig_size
            for obj in env.objects:
                if obj.type.name == "Sprite":
                    try:
                        tt = obj.read_typetree()

                        if "m_Rect" in tt:
                            tt["m_Rect"] = {
                                "x": 0.0,
                                "y": 0.0,
                                "width": float(w),
                                "height": float(h),
                            }

                        if "m_IsPolygon" in tt:
                            tt["m_IsPolygon"] = 0

                        if "m_PhysicsShape" in tt:
                            tt["m_PhysicsShape"] = []

                        if "m_RD" in tt:
                            rd = tt["m_RD"]

                            if "textureRect" in rd:
                                rd["textureRect"] = {
                                    "x": 0.0,
                                    "y": 0.0,
                                    "width": float(w),
                                    "height": float(h),
                                }

                            if "textureRectOffset" in rd:
                                rd["textureRectOffset"] = {"x": 0.0, "y": 0.0}

                            # Replace polygon mesh with a simple quad using packed vertex format.
                            # Stream 0: position XYZ (float32 * 3 = 12 bytes/vertex)
                            # Stream 1: UV XY (float32 * 2 = 8 bytes/vertex), packed after stream 0
                            if "m_VertexData" in rd and "m_IndexBuffer" in rd:
                                ppu = float(tt.get("m_PixelsToUnits", 100.0))
                                half_w = (w / 2.0) / ppu
                                half_h = (h / 2.0) / ppu

                                pos_data = struct.pack(
                                    "<12f",
                                    -half_w,
                                    -half_h,
                                    0.0,
                                    half_w,
                                    -half_h,
                                    0.0,
                                    half_w,
                                    half_h,
                                    0.0,
                                    -half_w,
                                    half_h,
                                    0.0,
                                )
                                uv_data = struct.pack(
                                    "<8f",
                                    0.0,
                                    0.0,
                                    1.0,
                                    0.0,
                                    1.0,
                                    1.0,
                                    0.0,
                                    1.0,
                                )
                                vd = rd["m_VertexData"]
                                vd["m_VertexCount"] = 4
                                vd["m_DataSize"] = pos_data + uv_data

                                # 2 triangles: (0,1,2) and (0,2,3), uint16 little-endian as byte list
                                rd["m_IndexBuffer"] = list(
                                    struct.pack("<6H", 0, 1, 2, 0, 2, 3)
                                )

                                if "m_SubMeshes" in rd and rd["m_SubMeshes"]:
                                    sm = rd["m_SubMeshes"][0]
                                    sm["firstByte"] = 0
                                    sm["indexCount"] = 6
                                    sm["firstVertex"] = 0
                                    sm["vertexCount"] = 4
                                    if "localAABB" in sm:
                                        sm["localAABB"] = {
                                            "m_Center": {"x": 0.0, "y": 0.0, "z": 0.0},
                                            "m_Extent": {
                                                "x": half_w,
                                                "y": half_h,
                                                "z": 0.0,
                                            },
                                        }

                        obj.save_typetree(tt)
                    except Exception as e:
                        print(f"Error processing sprite: {e}")
                        continue

        with open(f_path, "wb") as f:
            f.write(env.file.save(packer=APP_CONFIG.packer))

    def get_series_list(self) -> list[str]:
        """Get unique list of character series for filtering."""
        series_list = session.query(CharacterModel.series).distinct().all()
        return [series[0] for series in series_list if series[0]]
