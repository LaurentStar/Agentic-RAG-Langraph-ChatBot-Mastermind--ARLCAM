from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_base, sessionmaker
from ..app.constants import SocailMediaPlatform
from ..app.constants import CardType
from ..app.extensions import db

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
    card_types : Mapped[CardType] = mapped_column(unique=False) 

# 4. Create the table in the database
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
