from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_base, sessionmaker

# 1. Create an Engine
engine = create_engine('postgresql+psycopg://postgres:mysecretpassword@localhost:5432/postgres')

# 2. Define a Declarative Base
class Base(DeclarativeBase):
    pass

# 3. Define the new table as a Python class
class MyNewTable(Base):
    __tablename__ = 'my_new_table_orm'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String)

# 4. Create the table in the database
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

print("Table 'my_new_table_orm' created successfully.")
