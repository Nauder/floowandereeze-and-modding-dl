"""
Database models for the application.
This module defines all SQLAlchemy models used to store application data,
including configuration, card data, and various UI assets.
"""

from typing import ClassVar

from PySide6.QtGui import QIcon
from sqlalchemy import String, Integer, Boolean, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.objects import base, engine


# In theory all that inherit from this should have a `thumb: QIcon = QIcon()` attribute, but
# pyinstaller fails to detect the attribute, so it is explicitly declared in the children.
class UnityAsset:
    """
    Base class for Unity asset models.

    This class provides common fields for all Unity asset models:
    - id: Unique identifier
    - favorite: Whether the asset is marked as favorite
    - has_backup: Whether the asset has a backup

    Note: All child classes should have a `thumb: QIcon = QIcon()` attribute,
    but it's explicitly declared in children due to PyInstaller limitations.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    has_backup: Mapped[bool] = mapped_column(Boolean, default=False)


class AppConfig(base):
    """
    Application configuration model.

    Stores global application settings including:
    - Game path and background path
    - Version and crypto key
    - Mipmap settings and backup preferences
    - Background display mode
    """

    __tablename__ = "app_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mipmap_count: Mapped[int] = mapped_column(Integer, default=10)
    game_path: Mapped[str] = mapped_column(String(610))
    background_path: Mapped[str] = mapped_column(String(610), nullable=True)
    version: Mapped[str] = mapped_column(String(100), nullable=True)
    crypto_key: Mapped[str] = mapped_column(String(100), nullable=True)
    packer: Mapped[str] = mapped_column(String(5), default="LZ4")
    create_backup: Mapped[bool] = mapped_column(Boolean, default=False)
    background_mode: Mapped[str] = mapped_column(String(10), default="stretched")


class SleeveModel(UnityAsset, base):
    """
    Model for card sleeve assets.

    Stores information about card sleeves including:
    - bundle: Unique identifier for the sleeve asset
    - thumb: Thumbnail icon for the sleeve
    """

    __tablename__ = "sleeve"

    small_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    medium_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    thumb: QIcon = QIcon()


class CardModel(UnityAsset, base):
    """
    Model for card assets.

    Stores information about cards including:
    - name and description (original and modded)
    - bundle identifier
    - data index for Unity file
    - thumbnail icon
    """

    __tablename__ = "card"

    # Original card name and description are kept separate from metadata so restoration is possible
    name: Mapped[str] = mapped_column(String(255))
    large_bundle: Mapped[str] = mapped_column(String(8), unique=True, nullable=True)
    medium_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    small_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    unity_file: ClassVar[bool] = False
    thumb: QIcon = QIcon()


class FieldModel(UnityAsset, base):
    """
    Model for field assets.

    Stores information about field assets including:
    - bundle identifier
    - position flags (bottom, flipped)
    - thumbnail icon
    """

    __tablename__ = "field"

    small_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    medium_bundle: Mapped[str] = mapped_column(String(8), unique=True)
    thumb: QIcon = QIcon()


base.metadata.create_all(engine)
