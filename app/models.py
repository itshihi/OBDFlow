
"""
ORM(Object-Relation Mapper) 정의
데이터베이스 테이블과 클래스를 매핑한다.
"""

from sqlalchemy import Column, Integer, String, Nullable
from sqlalchemy.dialects.postgresql import ARRAY

from app.database import Base

class UUID(Base):
    __tablename__ = "uuids"

    id=Column(Integer, primary_key=True)
    service_uuid=Column(String)
    service_description=Column(String)
    characteristic_uuid=Column(String)
    characteristic_properties=Column(ARRAY(String))
    characteristic_description=Column(String)


class RawData(Base):
    __tablename__ = "raw_data"
    id=Column(Integer, primary_key=True)
    type=Column(String, Nullable=False)
    value=Column(String)
