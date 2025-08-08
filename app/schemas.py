
"""
fastapi의 요청과 응답 데이터의 유효성을 검사하는 pydantic 모델 정의
"""
from typing import List

from pydantic import BaseModel, ConfigDict


class UUIDBase(BaseModel):
    service_uuid : str
    characteristic_uuid : str
    characteristic_properties : str
    characteristic_description : str

class UUIDCreate(UUIDBase):
    pass

class UUID(UUIDBase):
    id : int
    model_config = ConfigDict(from_attributes=True)