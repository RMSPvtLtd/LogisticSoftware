from pydantic import BaseModel, ConfigDict


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: str | None
    email: str | None
    website: str | None
    tax_id_label: str | None
    tax_id: str | None
    company_reg_no: str | None
    is_default: bool
