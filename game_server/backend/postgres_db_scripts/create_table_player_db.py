
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_base, relationship, sessionmaker
from app.constants  import SocialMediaPlatform, CardType, PlayerStatus, PlayerStatus, ToBeInitiated
from app.extensions import db
from sqlalchemy.dialects.postgresql import ARRAY, ENUM as PG_ENUM



# 1. Create an Engine
database_name = 'player'
user = 'player_manager'
password = 'pm_manager1'
engine = create_engine(f'postgresql+psycopg://{user}:{password}@localhost:5432/{database_name}')

# 2. Define a Declarative Base
class Base(DeclarativeBase):
    pass

# # 3. Define the new table as a Python class
class Player(Base):
    # __bind_key__ = 'db_players'
    __tablename__ = 'player_table_orm'

    # ---------------------- Player Details ---------------------- #
    display_name                        : Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name  : Mapped[str] = mapped_column(unique=False)
    social_media_platform               : Mapped[SocialMediaPlatform] = mapped_column(unique=False) 
    card_types                          : Mapped[list[CardType]] = mapped_column(ARRAY(PG_ENUM(CardType, name="card_type_enum", create_type=True)))
    player_statuses                     : Mapped[list[PlayerStatus]] = mapped_column(ARRAY(PG_ENUM(PlayerStatus, name="player_status_enum", create_type=True)))
    coins                               : Mapped[int] = mapped_column(unique=False)

    # ---------------------- Who the player is targeting  ---------------------- #
    target_display_name                 : Mapped[str] = mapped_column(unique=False, nullable=True)
    to_be_initiated                     : Mapped[list[ToBeInitiated]] = mapped_column(ARRAY(PG_ENUM(ToBeInitiated, name="to_be_initiated_enum", create_type=True, nullable=True)))

    #---------------------- relationship to the Child tables ---------------------- #
    to_be_initiated_upgrade_details = relationship("ToBeInitiatedUpgradeDetails", back_populates="player")


# 4. Create the table in the database
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
print("Table 'player_table_orm'  created successfully.")
