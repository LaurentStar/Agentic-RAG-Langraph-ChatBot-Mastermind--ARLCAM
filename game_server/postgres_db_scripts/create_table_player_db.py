from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_base, sessionmaker
from constants  import SocailMediaPlatform, CardType, PlayerStatus
from extensions import db
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
    __tablename__ = 'player_table_orm'
    display_name : Mapped[str] = mapped_column(primary_key=True)
    social_media_platform_display_name: Mapped[str] = mapped_column(unique=False)
    social_media_platform : Mapped[SocailMediaPlatform] = mapped_column(unique=False) 
    card_types : Mapped[list[CardType]] = mapped_column(ARRAY(PG_ENUM(CardType, name="card_type_enum", create_type=True)))
    player_statuses : Mapped[list[PlayerStatus]] = mapped_column(ARRAY(PG_ENUM(PlayerStatus, name="player_status_enum", create_type=True)))

# 4. Create the table in the database
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
print("Table 'player_table_orm'  created successfully.")
