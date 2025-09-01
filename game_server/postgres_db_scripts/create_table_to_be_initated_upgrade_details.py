# Table representing event that are to transpire in the next update. Provide strongly typed data for player table
# Used as a way to shorten player table


import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_base, sessionmaker, relationship
from app.constants  import SocialMediaPlatform, CardType, PlayerStatus, PlayerStatus, ToBeInitiated
from app.extensions import db
from sqlalchemy.dialects.postgresql import ARRAY, ENUM as PG_ENUM

from create_table_player_db import Base

# 1. Create an Engine
database_name = 'player'
user = 'player_manager'
password = 'pm_manager1'
engine = create_engine(f'postgresql+psycopg://{user}:{password}@localhost:5432/{database_name}')


# 2. use the defined Declarative Base
#Base

# # 3. Define the new table as a Python class
class ToBeInitiatedUpgradeDetails(Base):
    __tablename__ = 'to_be_initiated_upgrade_details_table_orm'

    # ---------------------- To Be initiated details about the upgraded action ---------------------- #
    display_name            : Mapped[str] = mapped_column(ForeignKey("player_table_orm.display_name"), primary_key=True)
    assassination_priority  : Mapped[CardType] = mapped_column(unique=False)


    # ---------------------- relationship to the parent table ---------------------- #
    player = relationship("Player", back_populates="to_be_initiated_upgraded_details")

# 4. Create the table in the database
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
print("Table 'to_be_initiated_upgrade_details_table_orm'  created successfully.")
