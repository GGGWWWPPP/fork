from pydantic import BaseModel, EmailStr

# --- SCHEMAS (Модели входных данных) --- #
class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class PaymentCreateRequest(BaseModel):
    plan_type: str = "standard"
    duration_days: int
    devices_count: int

class ReferralApplyRequest(BaseModel):
    code: str

