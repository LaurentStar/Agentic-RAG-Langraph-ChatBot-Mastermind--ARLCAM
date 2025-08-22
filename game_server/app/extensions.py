from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


#=======================#
# SQL ALCHEMY EXTENSION #
#=======================#
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)


