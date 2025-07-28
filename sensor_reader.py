"""
    characteristic 에서 알림을 활성화한 뒤
    특정 데이터(rpm, 냉각수 온도, 속도 등)을 읽어올 수 있도록 ELM327 명령어를 write한다.
"""

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


async def main(bleaddress):
    async with (bleak.BleakClient(bleaddress) as client):

        response_received = asyncio.Event()
        response_queue = asyncio.Queue()

        # 수신 데이터 처리 방식을 정의
        async def notify_handler(sender, data):
            await response_queue.put(data)
            response_received.set()
            print(f"[HANDLER] {data} - {response_received}")

        write_char_uuid = []
        notify_char_uuid = []
        ACTIVE_WRITE_UUID = None
        ACTIVE_NOTIFY_UUID = None

        # 연결 확인
        if client.is_connected:
            print("Connected")
        else:
            print("Not connected")
            return

        # 모든 char uuid 의 properties 탐색
        for service in client.services:
            print(f"[SERVICE] {service.uuid} - {service.description}")
            for characteristic in service.characteristics:
                print(f"    [CHARACTERISTIC] {characteristic.uuid}-{characteristic.description}-{characteristic.properties}")
                if 'write' in characteristic.properties:
                    write_char_uuid.append(characteristic.uuid)
                if 'notify' in characteristic.properties:
                    notify_char_uuid.append(characteristic.uuid)

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

        print(f"[WRITE] {write_char_uuid}]")
        print(f"[NOTIFY] {notify_char_uuid}]")


        # 유효한 notify uuid 탐색
        for notify_uuid in notify_char_uuid:
            try:
                await client.start_notify(notify_uuid, notify_handler)
                ACTIVE_NOTIFY_UUID = notify_uuid
                print(f"[SET] Active Notify UUID: {ACTIVE_NOTIFY_UUID}")

                ###
                # 유효한 write uuid 탐색
                for uuid in write_char_uuid:
                    response_received.clear()
                    clear_cmd = b"ATZ\r"
                    await client.write_gatt_char(uuid, clear_cmd, response=True)

                    try:
                        await asyncio.wait_for(response_received.wait(), 10.0)  # 5초동안 응답 대기
                        while not response_queue.empty():  # 응답 수신 시 메시지 출력
                            data = await response_queue.get()
                            print(f"Received: {data.decode('ascii').strip()}")
                            ACTIVE_WRITE_UUID = uuid  # 사용가능한 uuid 할당
                            print(f"[SET] ACTIVE_WRITE_UUID: {ACTIVE_WRITE_UUID}")
                            break

                        if ACTIVE_WRITE_UUID:
                            break
                    except asyncio.TimeoutError:
                        print(f"[ERROR] Timeout with UUID {uuid}")
                    except Exception as e:
                        print(f"[ERROR] {e} with UUID {uuid}")

                if not ACTIVE_WRITE_UUID:
                    print("[ERROR] No valid write UUID found")
                    await client.stop_notify(ACTIVE_NOTIFY_UUID)
                    continue

            except Exception as e:
                print(e)

        ACTIVE_NOTIFY_UUID = "49535343-aca3-481c-91ec-d85e28a60318"
        ACTIVE_WRITE_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"


        # 다른 AT commands 입력
        for cmd in at_commands:
            try:
                await client.write_gatt_char(uuid, cmd, response=True)
                await asyncio.wait_for(response_received.wait(), 5.0)
                data = await response_queue.get()
                print(f"[RECEIVED] For {cmd} - {data.decode('ascii').strip()}")
            except asyncio.TimeoutError:
                print(f"[ERROR] Command {cmd} - Timeout with UUID {uuid}")
            except Exception as e:
                print(f"[ERROR] Command {cmd} - {e}")



        # rmp command 입력
        rpm_cmd = b"010C\r"
        # try:
        #     print("[REQUEST] RPM")
        #     await client.write_gatt_char(ACTIVE_WRITE_UUID, rpm_cmd, response=True)
        #     print("[REQUEST] RPM - waiting for response")
        #     await asyncio.wait_for(response_received.wait(), 60.0)
        #     data = await response_queue.get()
        #     print(f"[RECEIVED] {data.decode('ascii').strip()}")
        # except Exception as e:
        #     print(f"[ERROR] RPM command - {e} with UUID {ACTIVE_WRITE_UUID}")

        try:
            while True:  # RPM 데이터를 지속적으로 요청하기 위한 무한 루프
                response_received.clear()  # 다음 응답을 기다리기 위해 이벤트 플래그 초기화
                # 큐에 이전 응답이 남아있을 수 있으므로 비워주는 것이 좋음
                # while not response_queue.empty():
                #     await response_queue.get_nowait()  # 논블로킹으로 큐 비우기

                print(f"[REQUEST] Sending RPM command: {rpm_cmd.decode().strip()}")
                await client.write_gatt_char(ACTIVE_WRITE_UUID, rpm_cmd, response=True)
                print("[REQUEST] RPM - waiting for response...")

                try:
                    # 60초 대기는 너무 깁니다. RPM 응답은 보통 1초 내에 옵니다.
                    # 하지만 'SEARCHING...' 같은 메시지까지 포함하여 최대 5초 정도로 늘려볼 수 있습니다.
                    # 일단은 5초로 설정하고, 필요하면 더 늘리세요.
                    print("waiting f")
                    await asyncio.wait_for(response_received.wait(), 5.0)

                    # 응답이 들어왔으므로 큐에서 데이터를 모두 꺼내 처리 (SEARCHING... 포함)
                    while not response_queue.empty():
                        data = await response_queue.get()
                        decoded_data = data.decode('ascii', errors='ignore').strip()
                        print(f"[RECEIVED] {decoded_data}")

                        # 여기서 실제 RPM 데이터(예: '410CXXXX')를 파싱하는 로직 추가
                        if decoded_data.startswith("410C"):
                            rpm_hex_value = decoded_data[4:]
                            try:
                                A = int(rpm_hex_value[0:2], 16)
                                B = int(rpm_hex_value[2:4], 16)
                                rpm = ((A * 256) + B) / 4
                                print(f"    *** Parsed RPM: {rpm} ***")
                                # 여기에 RPM 데이터를 활용하는 추가 로직 (DB 저장, GUI 업데이트 등)
                            except ValueError:
                                print(f"    Error parsing RPM value: {rpm_hex_value}")
                        elif "SEARCHING" in decoded_data:
                            print(f"    Still searching for protocol...")
                        # 다른 ELM327 응답 메시지 (OK, ?, NO DATA 등)도 여기서 처리 가능
                        # ...

                except asyncio.TimeoutError:
                    print(f"[WARN] No response for RPM command within 5.0 seconds.")
                except Exception as e:
                    print(f"[ERROR] Error processing RPM response: {e}")

                await asyncio.sleep(0.5)  # 다음 RPM 요청까지의 짧은 지연 (예: 0.5초 또는 1초)

        except asyncio.CancelledError:  # Ctrl+C 등으로 프로그램이 종료될 때 발생
            print("\n[INFO] RPM data request interrupted by user.")
        except Exception as e:
            print(f"[CRITICAL ERROR] RPM command loop unexpected error: {e} with UUID {ACTIVE_WRITE_UUID}")
        finally:
            print("[INFO] Disabling notifications...")
            if ACTIVE_NOTIFY_UUID:
                try:
                    await client.stop_notify(ACTIVE_NOTIFY_UUID)
                except Exception as e:
                    print(f"[WARN] Error stopping notifications: {e}")


if __name__ == "__main__":
    asyncio.run(main(bleAddress))