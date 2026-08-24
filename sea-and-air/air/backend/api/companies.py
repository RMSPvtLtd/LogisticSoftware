from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models.company import Company
from schemas.companies import CompanyRead
from utils.security import get_current_ops_user
from services.companies import list_companies

router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(get_current_ops_user)])


@router.get("", response_model=list[CompanyRead])
def list_all(db: Session = Depends(get_db)) -> list[Company]:
    return list_companies(db)
