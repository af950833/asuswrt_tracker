# ASUSWRT Tracker

ASUSWRT 공유기에서 HTTP로 접속 기기 목록을 읽고, 사용자가 지정한 IP만 Home Assistant `device_tracker`로 추적하는 커스텀 통합입니다.

공유기에서 보이는 모든 기기가 Home Assistant에 등록되는 것을 막고, 가족 휴대폰처럼 필요한 기기만 재실 감지에 사용하기 위한 용도입니다.

## 주요 기능

- ASUSWRT HTTP 통신만 사용
- Config Flow 지원
- 사용자가 지정한 IP만 추적
- 지정한 IP만 `device_tracker` 엔티티로 생성
- 센서 생성 없음
- 공유기 기기 정보 생성 없음
- MAC 주소 관리/노출 없음
- 트래킹 IP에서 제거한 기기의 `device_tracker` 자동 삭제
- 여러 공유기 등록 가능
- 폴링 주기 설정 가능

## 요구 사항

- Home Assistant 2026.7.0 이상
- HTTP 관리 접속이 가능한 ASUSWRT 공유기
- 추적할 기기의 고정 DHCP/IP 할당

## 설치

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
| 트래킹 IP | 추적할 IP 목록. 한 줄에 하나씩 입력 |
| 폴링 주기 | 접속 기기 목록을 갱신할 주기. 기본값: `20`초 |

트래킹 IP 예시:

```text
192.168.0.59
192.168.0.60
192.168.0.61
192.168.0.62
192.168.0.63
192.168.0.64
```

## 옵션

통합 등록 후 옵션 화면에서 아래 항목을 수정할 수 있습니다.

- 트래킹 IP
- 폴링 주기

트래킹 IP 목록에서 IP를 제거하면 해당 IP의 `device_tracker` 엔티티도 Home Assistant에서 삭제됩니다.

## 엔티티 동작

트래킹 IP에 입력한 IP마다 하나의 `device_tracker` 엔티티가 생성됩니다.

예시:

```text
device_tracker.192_168_0_59
```

상태 판정:

- ASUSWRT HTTP 클라이언트 목록에서 해당 IP가 `CONNECTED` 상태이면 `home`
- 목록에 없거나 `CONNECTED`가 아니면 `not_home`

`consider_home` 지연은 적용하지 않습니다.

## 여러 공유기 등록

여러 개의 ASUSWRT Tracker 통합을 등록할 수 있습니다.

엔티티 `unique_id`는 아래 형식으로 생성됩니다.

```text
공유기_unique_id + 트래킹_IP
```

공유기 `unique_id`는 가능한 경우 공유기 MAC 주소를 사용하고, MAC 주소를 가져오지 못하면 설정한 호스트 값을 사용합니다.

이 방식으로 같은 IP를 여러 공유기에서 추적해도 `unique_id` 충돌을 피할 수 있습니다.

## 참고 사항

이 통합은 IP 주소를 기준으로 기기를 추적합니다. 안정적인 재실 감지를 위해 공유기에서 추적할 기기에 고정 DHCP/IP를 할당하는 것을 권장합니다.

공유기가 리부팅 중이거나 일시적으로 응답하지 않는 경우, 기존 상태를 유지하고 다음 폴링에서 다시 갱신을 시도합니다.

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

## 라이선스

MIT
