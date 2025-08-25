from app.constants import SocailMediaPlatform, CardType, PlayerStatus
from app.extensions import db
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from flask_restx import fields
from sqlalchemy.dialects import postgresql



class Player(db.Model):
    __bind_key__ = 'db_players'
    __tablename__ = 'player_table_orm'
    display_name : Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name: Mapped[str] = mapped_column(unique=False)
    social_media_platform : Mapped[SocailMediaPlatform] = mapped_column(unique=False) 
    card_types : Mapped[list[CardType]] = mapped_column(postgresql.ARRAY(postgresql.ENUM(CardType, name="card_type_enum", create_type=False)))
    player_statuses : Mapped[list[PlayerStatus]] = mapped_column(postgresql.ARRAY(postgresql.ENUM(PlayerStatus, name="player_status_enum", create_type=False)))



class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]


