import os

from pydantic_settings import SettingsConfigDict, BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

"""
    가장 일반적으로 db와 연결하고 sql을 삽입하는 방식
"""
#
# DB_HOST = "localhost"
# DB_PORT = 5433
# DB_NAME = "obdflow"
# DB_USER = "docker_user"
# DB_PASSWORD = "docker_user"
#
# try:
#     connection = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
#     cursor = connection.cursor()
#
#     cursor.execute(
#         """
#         CREATE TABLE uuids (
#             id SERIAL PRIMARY KEY,
#             service_uuid VARCHAR(32) NOT NULL,
#             characteristics_uuid  VARCHAR(32) NOT NULL,
#             characteristic_description VARCHAR,
#             properties VARCHAR
#         )
#         """
#     )
#
#     connection.commit()
#     print("Database created successfully")
#
#
# except (Exception, psycopg2.Error) as error:
#     print(error)

class Settings(BaseSettings):
    # postgresql+asyncpg 는 asyncpg 드라이버로 postgresql 을 사용하겠다는 의미
    DATABASE_URL: str = "postgresql+asyncpg://docker_user:docker_user@localhost:5433/obdflow"


    model_config = SettingsConfigDict(env_file="../.env")

settings = Settings()

# 비동기 엔진 생성
async_engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 비동기 세션 팩토리 생성
AsyncSessionLocal= async_sessionmaker(
    autocommit=False,
    autoflush=False, # 트랜잭션 자동 반영 방지
    bind = async_engine,
    class_ = AsyncSession # 비동기 세션을 사용할 것 암시
)

# ORM 생성하는 라이브러리 SQLAlchemy ORM 모델의 기본 클래스
Base = declarative_base()


# 의존성 주입을 위한 데이터베이스 세션 generator
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session # todo: yield 는 무슨 의미?

