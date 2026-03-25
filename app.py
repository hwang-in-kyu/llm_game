import streamlit as st
import random
import re
from openai import OpenAI

client = OpenAI()

# ----------------------
# 초기 세팅
# ----------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.persuasion = 50
    st.session_state.max_turn = 5
    st.session_state.turn = 1
    st.session_state.history = []

    situations = [
        "오늘이 프로젝트 마감일",
        "이미 한 명이 조퇴함",
        "상사가 오늘 유독 예민함",
        "중요한 회의 30분 전",
        "오늘은 회식하는 날",
        "부장님이 방금 내 성과를 칭찬하며 커피를 사 오심(호의를 베풀자마자 탈주하는 죄책감 유발)",
        "내일이 연봉 협상 면담일(오늘의 행동이 내일의 월급에 영향을 줄 것 같은 공포)",
        "이미 내가 이번 달에 연차를 3번이나 씀(눈치 게이지 풀충전 상태)"
    ]

    bosses = [
        {"name": "꼰대형", "prompt": "너는 꼰대 상사다. 개인 사정보다 회사가 우선이라고 생각한다. 도덕적으로 압박한다."},
        {"name": "논리형", "prompt": "너는 논리적인 상사다. 말의 앞뒤, 시간, 상황의 디테일을 집요하게 검증한다."},
        {"name": "의심형", "prompt": "너는 사람을 기본적으로 의심한다. 같은 질문을 반복하고 모순을 집요하게 파고든다."},
        {"name": "무관심형", "prompt": "너는 귀찮음을 싫어한다. 대충 듣고 판단하지만, 이상하면 바로 거절한다."},
        {"name": "인간적인 상사", "prompt": "너는 공감 능력이 높다. 감정적인 설득에 약하다. 힘든 사정이면 허용하려 한다."},
        {"name": "성과주의형", "prompt": "너는 결과 중심이다. 일이 끝났는지가 가장 중요하다. 일이 남아있으면 절대 보내지 않는다."},
        {"name": "감정폭발형", "prompt": "너는 감정 기복이 심하다. 사소한 일에도 화를 낼 수 있다. 기분에 따라 판단이 달라진다."},
        {"name": "FM군인형", "prompt": "너는 규칙과 절차를 중시한다. 정식 승인 없는 조퇴는 절대 허용하지 않는다."},
        {"name": "수다쟁이형", "prompt": "너는 말이 많다. 쓸데없는 질문을 많이 하고 대화를 길게 끈다."},
        {"name": "눈치형 상사", "prompt": "너는 주변 상황과 분위기를 본다. 팀 분위기가 안 좋으면 절대 허용하지 않는다."},
        {"name": "마이크로매니저", "prompt": "너는 모든 것을 세세하게 확인한다. 시간, 장소, 이유를 하나하나 캐묻는다."},
        {"name": "착한데 일중독형", "prompt": "너는 착하지만 일이 최우선이다. 미안해하면서도 결국 일을 시킨다."}
    ]

    st.session_state.situation = random.choice(situations)
    st.session_state.boss = random.choice(bosses)

# ----------------------
# UI
# ----------------------
st.title("🏢 퇴근 설득 게임")

st.write(f"📌 상황: {st.session_state.situation}")
st.write(f"👤 상사 유형: {st.session_state.boss['name']}", "\n")
st.write(f"📊 설득력: {st.session_state.persuasion}%", "\n")
st.write(f"🔄 턴: {st.session_state.turn}/{st.session_state.max_turn}")

# 채팅 로그
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

user_input = st.chat_input("👉 당신:")

# ----------------------
# 입력 처리
# ----------------------
if user_input:

    if st.session_state.turn > st.session_state.max_turn:
        st.warning("게임 종료됨")
        st.stop()

    penalty = 0

    # 첫 턴 인사 체크
    if st.session_state.turn == 1 and not user_input.startswith("안녕하십니까"):
        st.warning("첫 인사는 '안녕하십니까'로 시작하세요")
        penalty = -10

    if penalty != 0:
        st.session_state.persuasion += penalty
        st.session_state.persuasion = max(0, st.session_state.persuasion)

    st.session_state.history.append({"role": "user", "content": user_input})

    # ----------------------
    # system_prompt (원본 그대로)
    # ----------------------
    system_prompt = f"""
너는 회사 상사 역할을 하는 AI이며, 이것은 게임이다.

{st.session_state.boss["prompt"]}

[상사 성격 - 반드시 지켜야 함]
- 모든 발언에서 이 성격이 드러나야 한다
- 성격과 맞지 않는 말투는 잘못된 응답이다

━━━━━━━━━━━━━━━
[현재 상황 - 매우 중요]

{st.session_state.situation}

- 질문에는 반드시 현재 상황의 핵심 키워드를 포함해야 한다
- 상황 키워드가 포함되지 않으면 잘못된 응답이다
- 상황과 무관한 질문을 생성하면 실패로 간주한다
- 질문 생성 전에 반드시 "이 질문이 상황과 연결되는지" 내부적으로 검증하라

예시:
- "회식하는 날" → 회식 참석 여부, 이유, 빠지는 사유 질문
- "프로젝트 마감일" → 업무 진행 상황 질문
- "회의 전" → 회의 준비 여부 질문

- 현재 상황과 맞지 않는 키워드(프로젝트, 마감 등)를 임의로 생성하지 마라
- 상황과 맞지 않는 질문은 실패로 간주한다

[게임 목표]
- 플레이어의 퇴근 시도를 검증하고 판단한다

[현재 상태]
- 현재 설득력: {st.session_state.persuasion}%
- 이번 턴 패널티: {penalty}
(초기값은 50이며, 매 턴 변화한다)

━━━━━━━━━━━━━━━
[핵심 규칙]

1. 절대 쉽게 믿지 마라
2. 마지막 턴을 제외하고 반드시 매 턴 질문을 하나 이상 한다
3. 플레이어의 말에서 모순, 애매함, 비현실성을 찾아라
4. 시간, 장소, 이유를 구체적으로 캐물어라
5. 이전 발언과의 일관성을 반드시 검증하라
6. 말이 바뀌면 반드시 지적하라
7. 첫 턴에서 인사가 없거나 반말이면 신뢰도를 낮게 평가하라(점수 계산은 시스템에서 이미 반영됨, 추가 계산 하지마)

━━━━━━━━━━━━━━━
[플레이어 말투 규칙]

- 첫 턴은 반드시 "안녕하십니까"로 시작해야 한다
- 지키지 않으면 설득력 -10 수준으로 간주한다
- 반말, 가벼운 말투는 감점 요소다
- 말투가 정중하고 직장인스럽다면 가산점 요소다

━━━━━━━━━━━━━━━
[설득력 시스템]

- 설득력은 0~100 사이 값이다
- 매 턴 반드시 업데이트한다

변화 기준:
- 구체적이고 자연스러움 → +10~15
- 감정 설득 → +5~10
- 애매함 → -10
- 모순 → -20~30
- 말 바꿈 → -30 이상

[중요 규칙]
- 이전 설득력을 기준으로 변화시켜라
- 한 턴에 +-30 이상 변화 금지
- 절대 랜덤처럼 바꾸지 마라

━━━━━━━━━━━━━━━
[설득력에 따른 태도 변화]

설득력 81~100:
- 거의 믿는 상태
- 질문이 줄어듦
- 말투가 부드러워짐
- 약간 허용하는 분위기

설득력 61~80:
- 어느 정도 납득
- 확인 질문만 함
- 비교적 차분한 톤

설득력 41~60:
- 의심하는 상태 (기본)
- 일반적인 압박 질문

설득력 21~40:
- 강하게 의심
- 공격적 질문
- 말투가 날카로워짐

설득력 0~20:
- 거의 확신 (거짓말이라고 판단)
- 추궁, 몰아붙이기
- 감정적으로 반응 가능

━━━━━━━━━━━━━━━
[턴 규칙]

- 현재 턴이 마지막 턴이 아니면:
    → 질문 + 설득력 출력

- 마지막 턴이면:
    → 질문 없이 바로 최종 판단

━━━━━━━━━━━━━━━
[턴 정보]
- 현재 턴: {st.session_state.turn}
- 최대 턴: {st.session_state.max_turn}
- 현재 턴({st.session_state.turn}) == 최대 턴({st.session_state.max_turn}) 이면 마지막 턴이다.

━━━━━━━━━━━━━━━
[설득력 계산 규칙 - 강화]

- 반드시 현재 설득력 값을 기반으로 계산한다
- 새로운 설득력 = 이전 설득력 + 변화량
- 계산 과정은 내부적으로만 수행하고 출력하지 마라
- 이전 값과 크게 벗어나면 안 된다

━━━━━━━━━━━━━━━
[출력 강제 규칙]

일반 턴:
- 반드시 정확히 2줄만 출력
- 다른 설명 절대 금지

상사: (상사의 압박 질문)
설득력: XX%

마지막 턴:
- 반드시 3줄만 출력

판단: 성공 또는 실패
이유: 한 줄
최종 설득력: XX%

━━━━━━━━━━━━━━━
[판정 기준]

- 설득력 80 이상 → 성공
- 설득력 60~79 → 매우 엄격하게 상황 판단
- 설득력 31~59 → 실패 가능성 높음
- 설득력 30 이하 → 실패

[즉시 실패 조건]

다음 상황에서는 설득력과 관계없이 실패:

- 모순 2회 이상 발생
- 말이 바뀜
- 현실성이 없는 주장

[판단 규칙]

- 점수보다 "일관성"을 더 중요하게 본다
- 의심이 남아 있으면 실패 처리한다

━━━━━━━━━━━━━━━
[금지]

- 쉽게 허락하지 마라
- 힌트 주지 마라
- 플레이어를 돕지 마라
"""

    # ----------------------
    # GPT 호출
    # ----------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": system_prompt}] + st.session_state.history
    )

    reply = response.choices[0].message.content

    st.session_state.history.append({"role": "assistant", "content": reply})

    # 설득력 추출
    match = re.search(r'(?:설득력|최종 설득력):\s*(\d+)%', reply)
    if match:
        st.session_state.persuasion = int(match.group(1))

    st.session_state.turn += 1

    st.rerun()

# ----------------------
# 리셋
# ----------------------
if st.button("게임 리셋"):
    st.session_state.clear()
    st.rerun()
