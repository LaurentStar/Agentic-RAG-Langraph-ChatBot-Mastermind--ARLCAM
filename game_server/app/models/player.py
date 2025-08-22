from app.constants import SocailMediaPlatform
from app.constants import CardType
from app.extensions import db
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text


class Player(db.Model):
    display_name : Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name: Mapped[str] = mapped_column(unique=False)
    social_media_platform : Mapped[SocailMediaPlatform] = mapped_column(unique=False) 
    card_types : Mapped[CardType] = mapped_column(unique=False) 


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]


