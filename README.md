# CRDP Protect/Reveal 웹 데모 (API 전용)

브라우저에서 13자리 숫자를 입력해 원격 CRDP 서버에 protect → reveal을 요청하고, 진행 과정을 JSON으로 표시하는 데모입니다. 프런트엔드는 정적 파일이며, Flask 서버가 정적 서빙과 CORS 회피용 프록시를 제공합니다.

- Thales CRDP v1 스키마에 맞춰 `/v1/protect`, `/v1/reveal` 요청 바디/응답을 사용합니다.
- 진행 JSON에는 각 단계의 request/response만 누적됩니다(요약·시간 표시 없음).
- 기본 Host/Port는 `192.168.0.231:32082`입니다. 필요 시 URL 파라미터로 덮어쓸 수 있습니다.

참고: https://github.com/sjrhee/crdp_protect_reveal 의 진행 출력 개념을 UI에 맞게 단순화했습니다.

## 구성
- `index.html`, `app.js`, `style.css`: 프런트엔드 정적 파일
- `server.py`: Flask 서버. 정적 파일 서빙 + 프록시(`/proxy/v1/protect`, `/proxy/v1/reveal`)
- `requirements.txt`: 서버 의존성 목록(Flask, requests)

## 빠른 시작(venv 권장)

Linux bash 기준:

```bash
# 1) 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2) 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 3) 서버 실행 (기본 0.0.0.0:5000)
python server.py
```

브라우저에서 접속:
- http://localhost:5000

화면의 IP/Port/Protection Policy를 확인하세요. 기본값은 `192.168.0.231:32082`, `P03`입니다. CORS 회피를 위해 기본적으로 "프록시 사용"이 활성화되어 있습니다(권장).

URL 파라미터로 초기값을 지정할 수 있습니다:
- `?host=192.168.0.231&port=32082&policy=P03&data=1234567890123`

## 사용 방법
1) 데이터(13자리 숫자)를 입력합니다.
2) Protect → Reveal 실행 버튼을 누릅니다.
3) 결과 섹션에 protected/revealed 값이 표시되고, 진행 JSON 영역에 protect/reveal 단계의 요청·응답이 누적됩니다.

## 프록시 엔드포인트(서버)
- `POST /proxy/v1/protect` → 원격 `http://{host}:{port}/v1/protect`로 포워딩
- `POST /proxy/v1/reveal` → 원격 `http://{host}:{port}/v1/reveal`로 포워딩

요청 예시 바디(프록시 사용 시):
```json
{
  "host": "192.168.0.231",
  "port": "32082",
  "protection_policy_name": "P03",
  "data": "1234567890123"
}
```

고급 옵션:
- `scheme`: http 또는 https (기본값 http)
- `base_path`: 기본 경로(기본값 /v1). 예: `/api/v1` 등으로 바꿔야 할 때 사용

Protect/Reveal 사양 반영:
- Protect 응답에는 `protected_data`, `external_version`가 포함됩니다.
- Reveal 요청 시 `external_version`이 필요하면 사용자가 입력한 값을 우선 사용하고, 입력이 비어 있으면 Protect 응답의 `external_version`을 자동 전달합니다.

## 문제 해결 가이드
- 원격 CRDP 서버 접근이 되지 않으면 protect 단계에서 응답이 지연되거나 에러가 표시됩니다. 방화벽/네트워크를 확인하세요.
- CRDP 서버가 CORS를 허용하지 않는 경우 프록시를 사용해야 브라우저에서 호출이 가능합니다.
- 입력이 13자리 숫자가 아니면 프런트엔드가 즉시 검증 에러를 띄웁니다.

디버깅:
- 서버가 받은 원문과 파싱 결과를 확인하려면 디버그 라우트를 사용할 수 있습니다.
```bash
curl -sS -H 'Content-Type: application/json' \
  --data-binary @sample_protect.json \
  http://127.0.0.1:5000/proxy/_debug
```
개발 중에만 사용하고, 운영 반영 전에는 비활성화를 권장합니다.

## 라이선스
- 이 데모는 교육/테스트 목적입니다. 참고 레포의 출력 형식을 개념적으로 차용했으며, 해당 레포 라이선스를 확인하세요.
