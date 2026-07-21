# ASUSWRT Tracker

ASUSWRT 공유기에서 HTTP로 접속 기기 목록을 읽고, 사용자가 지정한 IP만 Home Assistant 엔티티로 생성하는 커스텀 통합입니다.

공유기에서 보이는 모든 기기가 Home Assistant에 등록되는 것을 막고, 가족 휴대폰처럼 필요한 기기만 재실 감지에 사용하기 위한 용도입니다.

## 주요 기능

- ASUSWRT HTTP 통신만 사용
- Config Flow 지원
- 지정한 IP만 엔티티로 생성
- `device_tracker`용 IP와 `binary_sensor`용 IP를 분리 입력
- `device_tracker`와 `binary_sensor`를 동시에 사용 가능
- 센서 생성 없음
- 공유기 기기 정보 생성 없음
- MAC 주소 관리/노출 없음
- IP 목록에서 제거한 기기의 엔티티 자동 삭제
- 여러 공유기 등록 가능
- 폴링 주기 설정 가능

## 요구 사항

- Home Assistant 2026.7.0 이상
- HTTP 관리 접속이 가능한 ASUSWRT 공유기
- 추적할 기기의 고정 DHCP/IP 할당

## HACS 설치

HACS에서 사용자 정의 저장소를 추가합니다.

```text
HACS > 우측 상단 메뉴 > 사용자 정의 저장소
```

저장소 URL:

```text
https://github.com/af950833/asuswrt_tracker
```

카테고리:

```text
Integration
```

저장소를 추가한 뒤 HACS에서 `ASUSWRT Tracker`를 설치하고 Home Assistant를 재시작합니다.

## 수동 설치

컴포넌트를 아래 경로에 복사합니다.

```text
custom_components/asuswrt_tracker
```

이후 Home Assistant를 재시작합니다.

## 설정

Home Assistant에서 아래 메뉴로 이동합니다.

```text
설정 > 기기 및 서비스 > 통합 추가 > ASUSWRT Tracker
```

입력 항목:

| 항목 | 설명 |
|---|---|
| 호스트 | ASUSWRT 공유기 IP 또는 호스트 이름. 예: `192.168.0.1` |
| 사용자 이름 | ASUSWRT 관리자 사용자 이름 |
| 비밀번호 | ASUSWRT 관리자 비밀번호 |
| Device tracker IP | `device_tracker`로 생성할 IP 목록. 한 줄에 하나씩 입력 |
| Binary sensor IP | `binary_sensor`로 생성할 IP 목록. 한 줄에 하나씩 입력 |
| 폴링 주기 | 접속 기기 목록을 갱신할 주기. 기본값: `20`초 |

둘 중 하나 이상의 IP 목록에는 값이 있어야 합니다.

Device tracker IP 예시:

```text
192.168.0.59
192.168.0.60
192.168.0.61
```

Binary sensor IP 예시:

```text
192.168.0.62
192.168.0.63
192.168.0.64
```

같은 IP를 두 목록에 모두 입력하면 `device_tracker`와 `binary_sensor`가 각각 생성됩니다.

## 옵션

통합 등록 후 옵션 화면에서 아래 항목을 수정할 수 있습니다.

- Device tracker IP
- Binary sensor IP
- 폴링 주기

IP 목록에서 제거한 기기의 엔티티는 옵션 저장 후 삭제됩니다.

## 엔티티 동작

### device_tracker

Device tracker IP에 입력한 IP마다 하나의 `device_tracker` 엔티티가 생성됩니다.

예시:

```text
device_tracker.192_168_0_59
```

상태 판정:

- ASUSWRT HTTP 클라이언트 목록에서 해당 IP가 `CONNECTED` 상태이면 `home`
- 목록에 없거나 `CONNECTED`가 아니면 `not_home`

`consider_home` 지연은 적용하지 않습니다.

### binary_sensor

Binary sensor IP에 입력한 IP마다 하나의 `binary_sensor` 엔티티가 생성됩니다.

예시:

```text
binary_sensor.192_168_0_62
```

상태 판정:

- ASUSWRT HTTP 클라이언트 목록에서 해당 IP가 `CONNECTED` 상태이면 `on`
- 목록에 없거나 `CONNECTED`가 아니면 `off`

`binary_sensor`의 device class는 `presence`입니다.

## 여러 공유기 등록

여러 개의 ASUSWRT Tracker 통합을 등록할 수 있습니다.

엔티티 `unique_id`는 공유기 고유값과 IP를 조합해서 생성합니다.

```text
공유기_unique_id + 트래킹_IP
```

공유기 `unique_id`는 가능한 경우 공유기 MAC 주소를 사용하고, MAC 주소를 가져오지 못하면 설정한 호스트 값을 사용합니다.

이 방식으로 같은 IP를 여러 공유기에서 추적해도 `unique_id` 충돌을 피할 수 있습니다.

## 참고 사항

이 통합은 IP 주소를 기준으로 기기를 추적합니다. 안정적인 재실 감지를 위해 공유기에서 추적할 기기에 고정 DHCP/IP를 할당하는 것을 권장합니다.

공유기가 리부팅 중이거나 일시적으로 응답하지 않는 경우, 기존 상태를 유지하고 다음 폴링에서 다시 갱신을 시도합니다.


## 라이선스

MIT

## 버전 히스토리

### 2026-07-21 / 1.1

- `binary_sensor` 생성 지원 추가
- Config Flow에서 `Device tracker IP`와 `Binary sensor IP` 분리 입력 지원

### 2026-07-20 / 1.0

- ASUSWRT HTTP 기반 IP allowlist `device_tracker` 지원
- 지정한 IP만 `device_tracker`로 생성
- 폴링 주기 설정 지원
- 여러 공유기 등록 시 충돌을 피하기 위한 unique ID 구조 적용
