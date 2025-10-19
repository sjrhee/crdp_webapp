// CRDP Protect/Reveal 브라우저 데모 (API 전용)
// Thales CRDP 문서(https://thalesdocs.com/ctp/con/crdp/1.2.1/crdp-apis/index.html)의 스키마에 맞춘 요청/응답 처리

const $ = (sel) => document.querySelector(sel);
const progressEl = $("#progress");
const protectedOutEl = $("#protected-out");
const revealedOutEl = $("#revealed-out");
const formEl = $("#pr-form");
const runBtn = $("#run-btn");
const resetBtn = $("#reset-btn");

// 진행 JSON 누적을 보기 좋게 관리
const progress = [];
function pushProgress(obj) {
  progress.push(obj);
  // Append so that order is protect -> reveal from top to bottom
  const entry = JSON.stringify(obj, null, 2) + "\n";
  progressEl.textContent += entry;
}

// API 호출 유틸
let extraProxyParams = {};

async function callApi({ host, port, path, body, useProxy }) {
  const url = useProxy ? `${path.replace('/v1/','/proxy/v1/')}` : `http://${host}:${port}${path}`;
  const headers = { "Content-Type": "application/json" };
  // For progress logging, capture ONLY the pure upstream JSON body (no proxy fields/headers/urls)
  const req = body;
  // But when actually sending, include proxy parameters if using proxy
  const finalBody = useProxy ? { host, port, ...extraProxyParams, ...body } : body;
  let resJson = null;
  let status = 0;
  try {
    const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(finalBody) });
    status = res.status;
    resJson = await res.json().catch(() => ({ raw: "<non-JSON>" }));
  } catch (err) {
    resJson = { error: String(err) };
  }
  return { request: req, response: resJson, status };
}

function validateInput13Digits(value) {
  return /^\d{13}$/.test(value);
}

resetBtn.addEventListener("click", () => {
  progress.length = 0;
  progressEl.textContent = "";
  protectedOutEl.textContent = "-";
  revealedOutEl.textContent = "-";
  // 원문 응답 섹션 제거됨
});


formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  runBtn.disabled = true;
  try {
    const data = $("#input-data").value.trim();
  const policy = $("#policy").value.trim() || "P03";
    const host = $("#host").value.trim();
    const port = $("#port").value.trim();
  const useProxy = $("#use-proxy")?.checked;

    // 입력 검증
    if (!validateInput13Digits(data)) {
      alert("13자리 숫자를 정확히 입력하세요.");
      return;
    }

    // 진행 JSON 골격(보낸 것/받은 것만 표시)
    const step = {
      protect: { request: null, response: null },
      reveal: { request: null, response: null },
    };

    // API 호출: CRDP 스펙에 맞춘 필드명 사용
    const protectReqBody = { protection_policy_name: policy, data };
  const pr = await callApi({ host, port, path: "/v1/protect", body: protectReqBody, useProxy });
  step.protect = { request: protectReqBody, response: pr.response };
  pushProgress({ stage: "protect", request: protectReqBody, response: pr.response });

    const protected_data = pr?.response?.protected_data;
    protectedOutEl.textContent = protected_data ? String(protected_data) : "<no protected_data>";

  // protect 실패 시 reveal 단계는 건너뜁니다.
  if (!protected_data) {
    pushProgress({ stage: "reveal", skipped: true, reason: "no protected_data from protect" });
    return;
  }

  const revealReqBody = { protection_policy_name: policy, protected_data };
  // external_version: protect 응답의 external_version을 자동 전달(필요 시 서버가 무시 가능)
  const autoExternalVersion = pr?.response?.external_version;
  if (autoExternalVersion) revealReqBody.external_version = autoExternalVersion;
  const rr = await callApi({ host, port, path: "/v1/reveal", body: revealReqBody, useProxy });
    step.reveal = { request: revealReqBody, response: rr.response };
    pushProgress({ stage: "reveal", request: revealReqBody, response: rr.response });

    const revealed = rr?.response?.data;
    revealedOutEl.textContent = revealed ? String(revealed) : "<no revealed>";

    // 요약/시간 관련 출력 제거
  } catch (err) {
    pushProgress({ error: String(err) });
    alert("에러: " + String(err));
  } finally {
    runBtn.disabled = false;
  }
});

// URL 파라미터 적용: ?host=192.168.0.231&port=32082&policy=P03&data=1234567890123
function applyParamsFromURL() {
  const p = new URLSearchParams(location.search);
  const host = p.get("host");
  const port = p.get("port");
  const policy = p.get("policy");
  const data = p.get("data");
  const scheme = p.get("scheme");
  const base_path = p.get("base_path");

  if (host) $("#host").value = host;
  if (port) $("#port").value = port;
  if (policy) $("#policy").value = policy;
  if (data) $("#input-data").value = data;

  // 프록시 호출 시 전달할 추가 파라미터(scheme/base_path)
  extraProxyParams = {};
  if (scheme) extraProxyParams.scheme = scheme;
  if (base_path) extraProxyParams.base_path = base_path;
}

applyParamsFromURL();
