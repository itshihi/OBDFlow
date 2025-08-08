import asyncio
import os

import uvicorn
from fastapi import FastAPI

from app import sensor_reader
from app.database import Base, async_engine


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        # models.py에서 정의한 테이블 생성
        await conn.run_sync(Base.metadata.create_all)

        sensor_reader_instance = sensor_reader.SensorReader(os.getenv("BLE_ADDRESS"))

        # create_task()로 비동기 함수를 백그라운드에서 실행, app이 종료될 때까지 유지
        try:
            await asyncio.create_task(sensor_reader_instance.reading_data())
        except asyncio.CancelledError:
            print("[ERROR] Sensor Reader Cancelled")


# @app.post("uuids/", response_model=UUIDSchema, status_code=status.HTTP_201_CREATED)
# async def create_uuid(uuid: UUIDCreate, db: AsyncSession = Depends(get_db)):
#     db_item = UUID(service_uuid = uuid.service_id, characteristic_uuid = uuid.characteristic_uuid, characteristic_description = uuid.description, characteristic_properties=uuid.characteristic_properties)
#     db.add(db_item)
#     await db.commit()
#     await db.refresh(db_item) # 커밋한 객체를 다시 db에서 로드 todo: 왜?
#     return db_item


def __main__():
    uvicorn.run(app, host="0.0.0.0", port=8000)
    if __name__ == "__main__":
        startup_event()