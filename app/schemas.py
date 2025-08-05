
"""
fastapi의 요청과 응답 데이터의 유효성을 검사하는 pydantic 모델 정의
"""
from pydantic import BaseModel, ConfigDict
from sqlalchemy.dialects.postgresql import array


class UUIDBase(BaseModel):
    service_id : str
    characteristic_uuid : str
    characteristic_properties : array
    characteristic_description : str

class UUIDCreate(UUIDBase):
    pass

class UUID(UUIDBase):
    id : int
    model_config = ConfigDict(from_attributes=True)