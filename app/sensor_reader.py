
from app.database import AsyncSessionLocal
from app.models import RawData, UUID

"""
0105	냉각수 온도
0106 / 0107	연료 트림 (단기/장기)
0122	연료 레일 압력
015E	엔진 연료 소비율
0104	엔진 부하
010C	엔진 RPM
0161 / 0162	요구 토크 / 실제 토크
0142	ECU 모듈 전압
0121	엔진 경고등 점등 후 주행 거리
0130 / 0131	고장 코드 초기화 이후 워밍업 횟수 & 주행 거리
010B	흡기 매니폴드 절대압
0110	공기 유량
"""

import asyncio
import bleak

bleAddress = "62E97F99-DF53-497B-85F5-171CA03CC4AE" # obdcheck의 uuid


class SensorReader:
    def __init__(self, ble_address):
        self.ble_address = ble_address
        self.client = bleak.BleakClient(self.ble_address)
        self.response_received = asyncio.Event()
        self.response_queue = asyncio.Queue()
        self.active_write_uuid = ""
        self.active_notify_uuid = ""


    # OBD 센서에서 데이터가 수신될 때마다 실행되는 함수
    # bytearray(b'41 0C 11 30 \r41 0C 11 2E \r')  와 같은 데이터를 str으로 변환
    async def notify_handler(self, sender, data):
        print("[HANDLER ORIGIN DATA]", data)
        # await self.response_queue.put(data)
        # str_data = data.decode("utf-8")
        # str_data.split(" ")
        # print("[HANDLER PARSED DATA]", str_data)
        await self.response_queue.put(data)
        self.response_received.set()  # todo: 얘를 추가 안해서 hexdecimal 에러 발생




        #todo: 데이터 전처리(파싱)


    async def save_data(self, ecu_type , value):
        async with AsyncSessionLocal() as session:
            try:
                rawdata = RawData(type=ecu_type, value=value)
                session.add(rawdata)
                await session.commit()
                await session.refresh()
            except Exception as e:
                await session.rollback()
                print("[SAVE ERROR]", e)


    # DB에
    async def reading_data(self):

        self.client = bleak.BleakClient(bleAddress)

        try:
            await self.client.connect()
        except Exception as e:
            print("[COnncet ERROR]", e)
            return

        # 센서 연결
        # try:
        #     await self.client.connect()
        #     print("[CONNECTED SUCCESS] " + self.ble_address)
        # except Exception as e:
        #     print(f"[CONNECTED ERROR] {e}")


        try:
            if self.client.is_connected:
                print("[CONNECTED SUCCESS]")
            else:
                print("[UNCONNECTED]")
        except Exception as e:
            print("[CONNECTED ERROR]", e)


        write_char_uuid = []
        notify_char_uuid = []

        at_commands = [
            # b"ATZ\r",  # ELM327 칩 리셋
            b"ATE0\r",  # Echo Off
            b"ATL0\r",  # Line Feeds Off
            b"ATH0\r",  # Headers Off
            b"ATSP0\r"  # Auto Protocol
        ]

        ecu_commands = [
            b'0105\r',
            b'0106\r',
            b'0122\r'
            b'015E\r',
            b'0104\r',
            b'010C\r',
            b'0161\r',
            b'0142\r',
            b'0121\r',
            b'0130\r',
            b'0131\r',
            b'010B\r',
            b'0110\r',
        ]


        # service와 characteristic UUID 탐색
        async with AsyncSessionLocal() as session:
            for service in self.client.services:
                for characteristic in service.characteristics:
                    try:

                        # postgresql DB에 UUID 정보 저장
                        service_data = UUID(service_uuid=str(service.uuid), characteristic_uuid=str(characteristic.uuid), characteristic_properties= ','.join(characteristic.properties), characteristic_description=str(characteristic.description))
                        session.add(service_data)
                        session.commit() # todo:/Users/sihyeon/PycharmProjects/OBDProject/app/sensor_reader.py:126: RuntimeWarning: coroutine 'AsyncSession.commit' was never awaited


                        # write/notify 권한 UUID 배열 생성
                        if 'write' in characteristic.properties:
                            write_char_uuid.append(characteristic.uuid)
                        elif 'notify' in characteristic.properties:
                            notify_char_uuid.append(characteristic.uuid)

                    except Exception as e:
                        print(f"[UUID ERROR] {e}")

            # todo: PID 수신 받을 수 있는 notify-write 조합이 따로 있음
            # 유효한 notify uuid 저장
            for notify_uuid in notify_char_uuid:
                try:
                    await self.client.start_notify(notify_uuid, self.notify_handler)
                    self.active_notify_uuid = notify_uuid
                    print("[ACTIVE NOTIFY UUID] " + self.active_notify_uuid)

                    # break

                    # 유효한 write uuid 저장 -> 데이터 수신 성공 여부 체크
                    for write_uuid in write_char_uuid:
                        clear_cmd = b"ATZ\r"
                        try:
                            self.response_received.clear()
                            await self.client.write_gatt_char(write_uuid, clear_cmd, response=True)
                            await asyncio.wait_for(self.response_received.wait(), timeout=5.0)

                            print("[ACTIVE WRITE UUID] " + self.active_write_uuid)

                            data = await self.response_queue.get()
                            if data is not None:
                                self.active_write_uuid = write_uuid
                                break

                        except asyncio.TimeoutError:
                            print(f"[WRITE ERROR] {write_uuid} timed out")

                except Exception as e:
                    print(f"[NOTIFY ERROR]{notify_uuid} -  {e}")





            # 나머지 at 커멘드 순차적으로 입력
            # todo: 중간에 안전하게 종료하는 법? -> ^c 를 눌러도 강제종료 불가능
            for at in at_commands:
                try:
                    self.response_received.clear()
                    await self.client.write_gatt_char(self.active_write_uuid, at, response=True)
                    await asyncio.wait_for(self.response_received.wait(), timeout=5.0) # 응답이 올 때까지 대기
                    data = await self.response_queue.get()
                    print(f"[AT COMMAND SUCCESS] ", at, ' ',  data)

                    if data is None:
                        print("[AT COMMAND ERROR] No Response" , at)
                except asyncio.TimeoutError:
                    print("[AT COMMAND TIME OUT ERROR]" , at)


            # ecu commands 동시 요청
            while True:
                tasks = []
                for ecu in ecu_commands:
                    async def write_single_ecu_command(ecu_cmd):# 각 명령어마다 독립적인 코루틴 생성
                        try:
                            self.response_received.clear()
                            await self.client.write_gatt_char(self.active_write_uuid, ecu_cmd, response=True)
                            await asyncio.wait_for(self.response_received.wait(), timeout=5.0)
                            while not self.response_queue.empty():
                                ecu_data = await self.response_queue.get()
                                print("[ECU DATA] ", ecu_cmd, ' ', str(ecu_data), '\n')

                                await self.save_data(ecu_data, str(ecu_data))
                        except asyncio.TimeoutError:
                            print(f"[WRITE ERROR] {ecu_cmd} timed out")
                        except Exception as e:
                            print(f"[WRITE ERROR] {e}")
                    async_write_single_ecu_command = write_single_ecu_command(ecu)
                    tasks.append(async_write_single_ecu_command)

                await asyncio.gather(*tasks)
