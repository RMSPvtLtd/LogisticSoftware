from pydantic import BaseModel, ConfigDict, Field, model_validator


class OpsUserRead(BaseModel):
    """Deliberately has no password_hash field -- it is never serialized,
    not just hidden by a frontend convention."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    is_active: bool


class OpsLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    ops_user: OpsUserRead


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=1)

    @model_validator(mode="after")
    def _confirmation_matches(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password do not match")
        return self
