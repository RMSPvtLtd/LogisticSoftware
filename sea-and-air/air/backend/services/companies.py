from sqlalchemy import select
from sqlalchemy.orm import Session

from utils.errors import NotFound
from models.company import Company


def list_companies(session: Session) -> list[Company]:
    return list(session.execute(select(Company).order_by(Company.id)).scalars())


def get_company(session: Session, company_id: int) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise NotFound(f"Company {company_id} not found")
    return company
