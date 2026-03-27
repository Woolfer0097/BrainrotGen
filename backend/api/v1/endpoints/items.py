from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.connector import get_db
from db.models import Item
from db.schemas import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[ItemRead])
def list_items(db: Session = Depends(get_db)) -> list[Item]:
    return db.query(Item).all()


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    exists = db.query(Item).filter(Item.name == payload.name).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item with this name already exists",
        )

    item = Item(name=payload.name, description=payload.description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
