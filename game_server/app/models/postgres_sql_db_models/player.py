from app.constants import SocialMediaPlatform, CardType, PlayerStatus, ToBeInitiated
from app.extensions import db
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey
from flask_restx import fields
from sqlalchemy.dialects import postgresql



class Player(db.Model):
    __bind_key__ = 'db_players'
    __tablename__ = 'player_table_orm'
    # ---------------------- Player Details ---------------------- #
    display_name                        : Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name  : Mapped[str] = mapped_column(unique=False)
    social_media_platform               : Mapped[SocialMediaPlatform] = mapped_column(unique=False) 
    card_types                          : Mapped[list[CardType]] = mapped_column(postgresql.ARRAY(postgresql.ENUM(CardType, name="card_type_enum", create_type=False)))
    player_statuses                     : Mapped[list[PlayerStatus]] = mapped_column(postgresql.ARRAY(postgresql.ENUM(PlayerStatus, name="player_status_enum", create_type=False)))
    coins                               : Mapped[int] = mapped_column(unique=False)
    # ---------------------- Who the player is targeting  ---------------------- #
    target_display_name : Mapped[str] = mapped_column(unique=False, nullable=True)
    to_be_initiated      : Mapped[list[ToBeInitiated]] = mapped_column(postgresql.ARRAY(postgresql.ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=False, nullable=True)))
    #---------------------- relationship to the Child tables ---------------------- #
    # to_be_initiated_upgrade_details = relationship("ToBeInitiatedUpgradeDetails", back_populates="player")


class ToBeInitiatedUpgradeDetails(db.Model):
    __bind_key__ = 'db_players'
    __tablename__ = 'to_be_initiated_upgrade_details_table_orm'
    # ---------------------- To Be initiated details about the upgraded action ---------------------- #
    display_name            : Mapped[str] = mapped_column(ForeignKey("player_table_orm.display_name"), primary_key=True)
    assassination_priority  : Mapped[CardType] = mapped_column(unique=False)
    # ---------------------- relationship to the parent table ---------------------- #
    # player = relationship("Player", back_populates="to_be_initiated_upgraded_details")

