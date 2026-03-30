from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.connector import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(4096), nullable=False)
