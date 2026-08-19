import pytest

from utils.errors import NotFound
from services.companies import get_company, list_companies
from factories import make_company


def test_list_companies(db_session):
    make_company(db_session, name="Company A")
    make_company(db_session, name="Company B", is_default=False)

    companies = list_companies(db_session)

    assert {c.name for c in companies} == {"Company A", "Company B"}


def test_get_company(db_session):
    company = make_company(db_session)
    fetched = get_company(db_session, company.id)
    assert fetched.id == company.id


def test_get_company_not_found(db_session):
    with pytest.raises(NotFound):
        get_company(db_session, 999999)


def test_companies_endpoint(client, db_session):
    make_company(db_session, name="Demo Freight Co")
    db_session.commit()

    r = client.get("/companies")
    assert r.status_code == 200, r.text
    assert any(c["name"] == "Demo Freight Co" for c in r.json())
