# WING 콘솔 조작 참고 자료 (AI 콘솔메이트용)

출처: Behringer WING / WING COMPACT / WING RACK 사용 설명서 영문판(2025년 9월 4일판, 163쪽) 내용을 요약했습니다.
괄호 안 p.숫자는 설명서 쪽 번호입니다. "설명서에서 확인 못 함"이라고 적힌 항목은 일반 지식이므로,
안내할 때 "콘솔 화면에서 이름을 확인해 주세요"라고 덧붙이세요. 펌웨어 버전에 따라 화면이 설명서 그림과 다를 수 있습니다(p.2).

## 1. 신호의 흐름 (p.6-8)
- 소스(Source): 실제 입력(마이크·악기 단자, 스테이지박스 등). 소스마다 이름·색·아이콘·게인·뮤트·위상·팬텀이 있습니다.
- 소스 그룹: Local In(WING 본체 프리앰프 8개), Aux In(본체 라인 입력 8개), AES/EBU, AES50 A/B/C(스테이지박스, 각 48), StageConnect, USB Audio(48), USB Player, 확장 카드(WING-LIVE 등), 내부 모듈.
- 채널(Channel): 소스를 받아 처리(필터, 게이트, EQ, 컴프 등)하는 곳. 입력 채널 40개 + Aux 채널 8개. 채널마다 MAIN·ALT 두 입력을 지정하고 바꿀 수 있습니다.
- 버스(Bus) 16개(B1-B16, 모두 스테레오): 모니터 믹스나 이펙트 보내기에 씁니다. 채널별·버스별로 모드가 다릅니다.
  - TAP: 채널의 TAP 지점(보통 페이더 앞)에서 보냄 → 모니터 믹스에 적합. 메인 페이더를 움직여도 모니터 크기가 안 바뀜.
  - POST: 페이더 뒤에서 보냄 → 리버브·딜레이 보내기에 적합.
  - GROUP: 센드 없이 채널 페이더를 그대로 따라감(그룹 처리용).
- 메인(Main) 4개(M1-M4, 스테레오): 채널마다 메인 4개로 각각 따로 보낼 수 있고, 각각 페이더 앞/뒤를 정할 수 있습니다. 설명서 예시도 "하나는 PA, 하나는 라이브 방송"입니다.
- 매트릭스(Matrix) 8개(MX1-MX8): 메인·버스를 받아 출력 단자로만 내보냅니다(다른 버스로는 못 보냄). 예: 로비, 자모실 스피커.
- 내부 소스: 버스·메인·매트릭스를 다시 채널 입력으로 쓸 수 있고, 테스트 신호(사인파, 핑크/화이트 노이즈), User Signals, User Patches가 있습니다.

## 2. 콘솔 겉면 (p.13-28)
- 화면 왼쪽 7개 버튼과 각 구역의 VIEW 버튼으로 화면을 고릅니다: HOME, EFFECTS, METERS, ROUTING, SETUP, LIBRARY, UTILITY.
  화면 아래 6개 터치 노브로 아래쪽 값을 바꾸고, 화면 오른쪽 노브로 미세 조정합니다.
- 페이더 구역 3개(WING 기준, p.14-15)
  - 왼쪽 12개: 입력 채널(레이어 INPUTS 1-40, AUX IN 등).
  - 가운데 8개: 보통 버스와 DCA.
  - 오른쪽 4개: 보통 메인과 매트릭스.
  - 기본 레이어: INPUTS, AUX IN, BUS MASTER(버스 1-16), MAIN MATRIX(메인 1-4, 매트릭스 1-8), DCA(1-16), USER 1·2(비어 있음).
- 채널 스트립(p.22): 위쪽 버튼 줄 = MUTE, 아래쪽 버튼 줄 = SOLO. 미터는 -60 dB부터 클립까지 표시. CLR SOLO로 솔로 전부 해제(p.14).
- 채널 이름·아이콘·색: 채널 HOME 화면의 NAME / ICON / COLOR 탭에서 바꿉니다(p.19, 31).
  - LINK CUSTOMIZATION TO SOURCE를 켜면 소스와 채널의 이름·색·아이콘이 같이 바뀌고, 끄면 따로입니다(p.31).
  - 그래서 콘솔에 보이는 채널 이름과 소스 이름이 다를 수 있습니다.
- SELECT를 누르면 그 채널이 선택되고, HOME 화면에서 모든 처리 설정이 보입니다. HOME에서 채널 번호를 누르면 채널 선택 창이 열립니다(p.30).

## 3. 모니터 믹스 만들기 / 조절하기 (p.7-8, 28, 63)
- 방법 1 - Sends On Faders(SOF, p.28):
  1) 가운데 또는 오른쪽 구역에서 원하는 버스(모니터)·메인·매트릭스를 선택(SELECT)
  2) SOF FLIP 버튼을 누름
  3) 이제 왼쪽 채널 페이더가 그 모니터로 "보내는 양"이 됩니다. 채널 뮤트를 풀면 그 센드가 켜집니다.
  4) 끝나면 SOF FLIP을 다시 눌러 원래대로.
  - BUS MASTER 레이어의 버스 버튼을 눌러도 그 버스의 SOF가 켜집니다(p.16).
  - 주의: SOF 상태에서 페이더를 움직이면 메인 소리가 아니라 모니터 센드가 바뀝니다. 예배 중 SOF가 켜져 있는지 꼭 확인하세요.
- 방법 2 - SENDS 화면(p.63): OVERVIEW/FADERS 옆 SENDS 아이콘 → 오른쪽 위에서 대상 버스 선택(BUS 1-8, BUS 9-16, MAIN, MATRIX) → 화면 페이더로 조절.
- 방법 3 - 채널 HOME 화면의 버스 센드 부분에서 버스별 레벨·켜짐·모드(TAP/POST/GROUP)를 정합니다.
- P16 같은 개인 모니터는 보통 버스를 출력으로 보내 사용합니다. 출력 지정은 ROUTING → OUTPUTS(5절).

## 4. 메인과 매트릭스 (p.7-8, 16, 76)
- MAIN MATRIX 레이어 버튼 1-4는 메인 1-4의 SOF, 9-16은 매트릭스 1-8의 SOF를 켭니다(p.16).
- 아무 버튼도 안 누른 상태에서 오른쪽 메인 페이더는 MAIN 1을 조절합니다(SETUP → SURFACE → MAIN FADER → SOURCE에서 변경 가능).
- 메인 채널에는 다이내믹스, 8밴드 EQ, 인서트, 출력 딜레이, 매트릭스 센드(Matrix Sends)가 있습니다(p.76). 메인에서 매트릭스로 보내는 양은 메인 채널의 Matrix Sends에서 정합니다.

## 5. 라우팅 (p.38-41)
- ROUTING 화면 위쪽 버튼으로 세 화면을 바꿉니다: CHANNELS / SOURCES / OUTPUTS.
  - CHANNELS: 왼쪽에서 채널(입력 40 + Aux 8)을 고르고, 오른쪽에서 그 채널에 넣을 소스를 지정. MAIN/ALT 입력 전환.
  - OUTPUTS: 실제 출력 단자(왼쪽)마다 어떤 신호를 내보낼지(오른쪽) 지정. 드롭다운으로 소스 그룹을 고릅니다. 예: 버스 3을 스테이지박스 출력으로.
  - MONITOR 소스 그룹에는 PHONES와 SPEAKERS가 있어 원하는 출력으로 보낼 수 있습니다.
- 라우팅 변경은 소리가 통째로 사라질 수 있는 작업입니다. 예배 중에는 하지 말고, 바꾸기 전 스냅샷을 저장하도록 안내하세요.

## 6. 입력 채널 처리 (p.67-73)
- 처리 순서는 HOME 왼쪽 아래 렌치 아이콘으로 바꿀 수 있습니다. GATE, EQ, COMP, INS1은 항상 페이더 앞, INS2는 항상 페이더 뒤입니다(p.67).
- INPUT 슬롯(p.67-68)
  - TRIM: 디지털 레벨 ±18 dB. BALANCE: 좌우 균형(모노 소스에는 효과 없음). INVERT: 위상 반전.
  - FILTER: 로우컷(LC FREQ, 기울기 6/12/18/24 dB/oct), 하이컷(HC FREQ, 6/12 dB/oct), 툴 필터(Tilt EQ, Maxer, All-Pass).
  - 말소리·보컬의 웅웅거림이나 무대 진동 소음에는 로우컷을 켭니다. 보통 보컬 80~120 Hz, 설교 마이크 100~150 Hz (일반 지식).
- 프리앰프 게인과 +48V 팬텀은 소스(입력) 설정에 속합니다(p.6). 정확한 버튼 위치는 설명서에서 확인 못 함 → 채널 HOME의 INPUT 부분이나 ROUTING → SOURCES에서 찾도록 안내하세요.
  - 팬텀(+48V)은 콘덴서 마이크·DI용입니다. 켜고 끌 때 "펑" 소리가 날 수 있으니 그 채널을 먼저 뮤트하세요 (일반 지식).
- 각 슬롯 화면 위쪽 드롭다운에서 처리기 종류를 고르고, 주요 값은 화면 아래 노브로 조절합니다(p.69-70).
- GATE 슬롯(p.69): 기본은 Gate/Expander. 그 밖에 덕커(ducker), 아날로그 게이트, 컴프, Wave Designer, Auto Rider, Dynamic EQ 등을 넣을 수 있습니다.
  - KEY SOURCE(다른 채널을 트리거로), KEY FILTER, KEY SOLO, ACCENT(열릴 때 잠깐 키움) 등이 있습니다. 문턱값·범위 등 세부 이름은 설명서에서 확인 못 함.
- EQ 슬롯(p.69-70): WING EQ와 아날로그 EQ 모델. 입력 최대 6밴드, 버스 8밴드(p.22).
  - RTA(주파수 분석 그림)가 EQ 화면에 함께 표시되고, FREEZE로 멈춰 볼 수 있습니다. RTA 설정은 EQ 화면 오른쪽 위 SETTINGS.
  - BAND SOLO: 고른 밴드의 주파수만 솔로로 들어 봅니다 → 하울링 주파수 찾기에 유용.
  - MIX: EQ 전체 효과의 양(100% = 설정대로). LO CUT / HI CUT 버튼으로 INPUT 슬롯의 필터를 켜고 끕니다.
  - 겉면에서 조절(p.22): EQ 버튼을 누른 채 EQ 노브 4개 중 하나를 터치 → GAIN / WIDTH / FREQ 선택, SHIFT로 로우/하이 쉘프, LISTEN으로 밴드 솔로.
- COMP 슬롯(p.70): WING Compressor, Expander, 아날로그 컴프, Wave Designer, Auto Rider.
  - GAIN(메이크업), AUTO ENV(어택·홀드·릴리즈 자동), DETECTOR(RMS/PEAK), XOVER MODE(특정 대역만 압축). 문턱값·비율 세부는 설명서에서 확인 못 함.
- INS 1 / INS 2(p.70): FX PROCESSOR에서 16개 FX 슬롯 중 하나를 지정 → FX TYPE으로 효과 선택.
- AUTOMIX 자동 믹스(p.71): 입력 채널 INS 2 슬롯 위쪽을 FX → AUTO-X 또는 AUTO-Y로 바꾸면 켜집니다. X·Y 두 그룹.
  - 말하는 사람 마이크만 자연스럽게 크게, 나머지는 자동으로 줄여 줍니다. 여러 명이 말하는 기도회·패널 토론의 마이크 여러 개에 좋습니다.
  - 켜고 끄는 스위치는 SETUP → AUDIO → AUTOMIX에도 있습니다(p.47).
- MAIN SENDS(p.71): 메인 1~4로 보내는 양이 화면 왼쪽에. PRE 버튼으로 그 메인만 페이더 앞으로. 가운데에 PAN과 WIDTH(-150%~+150%).
- BUS / MATRIX SENDS(p.72-73): Sends 슬롯 아래쪽 절반은 버스 센드, 위쪽 절반은 매트릭스 센드(PAGE 노브나 슬롯 두 번 클릭으로 전환).
  - 센드의 PAN 노브를 누르면: MODE(TAP/POST/GROUP), IGNORE CHANNEL MUTE(TAP 모드에서 채널을 뮤트해도 모니터 센드는 유지), LINK SEND PAN TO CHANNEL PAN.
  - TAP WIDTH, TAP EQ(모니터용 3밴드 EQ)도 있습니다.
## 7. DCA와 뮤트 그룹 (p.16, 31, 65)
- DCA 16개: 여러 채널의 페이더를 한 번에 올리고 내리는 리모컨. 예: 보컬 DCA, 악기 DCA.
  - 지정: 채널 HOME의 TAGS 탭에서 DCA 태그를 붙이거나, 메인 페이더 구역의 SELECT를 누른 채 원하는 채널들의 SELECT를 누르고 뗍니다(p.16).
  - DCA 버튼을 누르면 그 DCA에 속한 채널들이 왼쪽 구역에 펼쳐집니다.
- 뮤트 그룹 8개: 여러 채널을 한 번에 뮤트. CONFIG 옆 MUTEGRP → 그룹 칸을 눌러 채널을 고릅니다(p.65). 채널 HOME의 TAGS 탭에서도 지정합니다(p.31).

## 8. 솔로, 헤드폰·모니터 스피커, 토크백 (p.24, 31, 45-46, 79-81)
- 겉면(p.24): PHONES 노브 = 헤드폰, MONITOR 노브 = 모니터 스피커. DIM은 소리 줄이기(길게 = 뮤트), MONO는 모노(길게 = 좌우 바꾸기). TALK LEVEL, TALK A, TALK B.
- MONITORS 화면(p.79-81): 모니터 구역의 VIEW 또는 SETUP → MONITORS.
  - 왼쪽: TALK A / TALK B, PHONES / SPEAKERS / PH+SPK(조절할 경로 선택), DIM, MUTE, MONO, LR SWAP.
  - 오른쪽(헤드폰·스피커 각각): SOURCE(평소에 들을 것: Main 1-4, Matrix 1-8, Bus 1-16, Aux 1-8), SRC MIX(솔로 중에도 원래 소리를 이만큼 섞기), DIM, PFL DIM, BAND SOLO, 8밴드 EQ, 딜레이, 리미터.
- 토크백(p.80): TALK A, TALK B를 따로 설정.
  - SWITCH MODE: AUTO(누르고 있으면 그동안만, 짧게 누르면 켜짐 유지), PUSH(누르는 동안만), LATCH(다시 누를 때까지).
  - TALK TO BUS / TALK TO MATRIX / TALK TO MAIN에서 말이 나갈 곳을 고릅니다. 예: 찬양팀 모니터 버스들만.
  - AUTO DIM: 토크백 중 버스(BUS DIM)와 내 모니터(MON DIM)를 얼마나 줄일지.
  - 토크백을 쓰려면 SETUP → AUDIO → PREFERENCES의 TALKBACK을 켜고 토크백용 채널(채널 40 또는 Aux 8)을 고릅니다(p.45). 토크백 마이크를 그 채널에 연결해 씁니다.
  - 채널 TAGS의 TALK ON / TALK SOLO 태그로 토크백 중 특정 채널을 켜거나 솔로할 수 있습니다(p.31).
- 솔로 방식(SETUP → AUDIO → SOLO SYSTEM, p.45-46)
  - LIVE / STUDIO: 솔로는 내 헤드폰·모니터에만 영향(메인·버스 소리는 그대로) → 예배 중 안전.
  - SIP(Solo In Place): 솔로하지 않은 채널을 실제로 뮤트합니다 → 예배 중에는 위험하니 쓰지 마세요.
  - 채널마다 PFL(페이더 앞)/AFL(페이더 뒤) 솔로. EXCLUSIVE SOLO = 한 번에 하나만. CLR SOLO로 전부 해제(p.14).
## 9. 씬과 스냅샷 - LIBRARY (p.51-59)
- LIBRARY 화면 왼쪽: 내부 저장소, USB, Show 파일 안의 파일들. 오른쪽 탭: SHOW, SNAP(스냅샷), SNIP(스니펫), CLIP, FX, CHAN(채널 프리셋)(p.52).
- 스냅샷(SNAP)은 항상 모든 값을 저장하지만, 불러올 때는 범위(Scope)에 든 것만 불러옵니다(p.53-54).
  - SAVE: 새 스냅샷 저장 / SAVE + SCOPE: 범위를 정해 저장 / UPDATE: 범위 안의 변경을 덮어쓰기 / PARTIAL UPDATE: 고른 항목만 덮어쓰기
  - LOAD: 범위대로 불러오기 / PARTIAL LOAD: 고른 항목만 불러오기 / EDIT SCOPE: 범위 수정
  - RESTORE: 범위를 무시하고 전부 불러오기. 보호(GLOBAL)해 둔 값까지 덮어씁니다. 예배 중에는 쓰지 마세요.
  - Scope 항목(p.55-56): 입력 채널, Aux, 버스, 메인, 매트릭스, 소스·출력 그룹(라우팅), DCA, 뮤트 그룹, FX 슬롯, 콘솔 설정 등. 채널 안에서도 이름·태그·입력·필터·게이트·EQ·컴프·센드·페이더·뮤트 등을 따로 고를 수 있습니다.
- 불러오기 보호: Scope 창의 GLOBAL 버튼으로 표시한 항목은 다른 씬을 불러와도 바뀌지 않습니다. 하나라도 지정하면 GLOBAL 아이콘이 빨갛게 됩니다(p.56). NO GLOB을 켜고 불러오거나 RESTORE를 쓰면 이 보호도 무시됩니다(p.54).
- 실수로 불러오기 방지: SETUP → GENERAL → OPERATION의 CONFIRM LIBRARY LOAD를 켜면 불러올 때마다 확인 창이 뜹니다(p.43). 봉사자용 콘솔에는 켜 두기를 권합니다.
- 스니펫(SNIP, p.57): 일부 값만 바꾸는 작은 저장. REC → 값 바꾸기 → STOP → SAVE. LOAD로 그 변경만 다시 적용.
- 채널 프리셋(CHAN, p.59): 한 채널의 설정을 저장해 다른 채널에 적용. FX 프리셋(FX, p.59): FX 슬롯 설정 저장.
- 클립(CLIP, p.58): 콘솔에 저장한 WAV 파일 재생(2/4트랙, 44.1/48 kHz). 소리가 나오려면 ROUTING에서 재생 채널을 지정해야 합니다.
- SHOW 파일(p.52-53): 스냅샷·스니펫 등을 순서대로 모아 둔 것(각각을 Scene이라 부름). GO로 선택한 씬 불러오기, GO NEXT / GO PREV. SKIP, LINK, 태그(#1~#128)로 커스텀 컨트롤에서 불러오기.
- 켤 때 자동으로 불러오기: 파일 이름을 "STARTUP"으로 시작하게 하고 저장 장치 맨 위 "STARTUP" 폴더에 둡니다(p.52). 켤 때 LIBRARY를 누르고 있으면 자동 불러오기를 건너뜁니다(p.89-90).
- 안전 수칙: 예배 전에 SNAP → SAVE로 현재 상태를 새로 저장해 두세요(UPDATE는 덮어쓰기).
- 이 프로그램(AI 콘솔메이트)은 아직 스냅샷을 불러오지 못합니다. 콘솔 LIBRARY 화면에서 직접 하도록 안내하세요.
## 10. 이펙트 (p.36)
- EFFECTS 화면: FX 랙 16개. 1-8번은 고급(Premium, 리버브·딜레이 등), 9-16번은 표준 이펙트와 채널 스트립.
- 리버브·딜레이는 보통 버스 센드(POST 모드)로 보내서 씁니다. 앰프 시뮬레이터 등은 인서트로 씁니다.
- 채널의 GATE·EQ·COMP 자리에 넣은 이펙트는 지연이 없고, 인서트는 약간의 지연이 생깁니다.

## 11. 미터와 하울링 찾기 (p.14, 22, 37, 62, 69-70)
- METERS 화면은 DCA, 메인, 매트릭스 등 종류별로 미터를 모아 보여주고, 누르면 FADERS 화면으로 갑니다(p.37).
- FADERS 화면(p.62): 채널마다 화면 페이더와 게이트·컴프 동작 표시(초록 = 게이트 열림).
- RTA(주파수 분석)는 채널 EQ 화면에 함께 표시됩니다(FREEZE로 멈춤, SETTINGS에서 설정). 하울링이 나면 EQ 화면 RTA에서 튀는 주파수를 보고, BAND SOLO로 확인한 뒤 그 밴드를 살짝 깎습니다(p.69-70).
- 하울링 자동 탐지 기능은 설명서에서 확인 못 함.
## 12. 설정, 원격, 잠금, 녹음, 전원 (p.24, 41-50, 82-90)
- SETUP 탭: General, Audio, Surface, Remote, DAW(p.41). 오른쪽 위에는 항상 INITIALIZE CONSOLE과 SHUTDOWN이 있습니다.
  - INITIALIZE CONSOLE은 설정 초기화입니다. 봉사자에게는 절대 누르지 말라고 안내하세요.
  - 끌 때: SHUTDOWN → "IT IS SAFE TO SWITCH DOWN THE CONSOLE" 표시 후 전원을 끕니다. 그 화면에서 다시 켜려면 EFFECTS를 누른 채 HOME(p.41).
- GENERAL(p.43-44): 콘솔 이름(원격 앱에 표시), 날짜·시간, 펌웨어 UPDATE, CONFIRM LIBRARY LOAD, ALWAYS SHOW ACTIVE SCENE, 밝기.
- AUDIO(p.44-47): 샘플레이트·클럭, INPUT SELECT(MAIN/ALT 일괄 전환), PREFERENCES, SOLO SYSTEM, USB AUDIO 채널 수, AUTOMIX.
  - STARTUP MAIN MUTE: 켜면 콘솔을 켤 때 메인이 뮤트된 채로 시작합니다(p.45). 켤 때 스피커 "펑" 방지용. 이 설정이 켜져 있으면 예배 전에 메인 뮤트를 풀어야 소리가 납니다.
  - MAIN LINK: MAIN 1 레벨을 다른 메인과 연동(p.45). DCA MUTEGROUPS: DCA를 뮤트 그룹처럼(p.45).
- SURFACE(p.47-49): 미터 설정, SEL DBL CLICK, SOF 버튼 표시(SHOW SOF FRAME: SOF 중 화면 왼쪽 위에 노란 테두리), ALTERNATIVE SOF MODE, 페이더 모터 속도, DCA SPILL 등.
- REMOTE(p.49-50)
  - NETWORK: DHCP 또는 고정 IP. 콘솔은 랜선으로 공유기/스위치에 연결하고, 원격 기기는 같은 네트워크에 있어야 합니다. 최대 16대 동시 원격.
  - 공식 앱: WING Edit(PC: Mac·Windows·Linux), WING Copilot(태블릿·폰), WING Q(개인 모니터용 폰 앱).
  - REMOTE LOCK: 켜면 OSC(UDP 2223)와 TCP 2222 원격 조작이 막힙니다 → 이 프로그램(AI 콘솔메이트)도 조작할 수 없게 됩니다. 연결 오류 시 이것을 먼저 확인하세요.
- 화면·버튼 잠금(p.89-90): HOME을 길게 누르면 겉면과 터치 화면이 잠깁니다(소리와 원격 조작은 그대로). HOME과 다른 버튼 조합을 비밀번호처럼 정할 수 있고, 다시 HOME(+조합)을 길게 눌러 풉니다. 콘솔을 다시 켜도 풀립니다.
  - 잠긴 동안 METERS 화면을 보여주려면 SETUP → GENERAL의 SHOW METER PAGE WHEN LOCKED(p.43).
- 그 밖의 단축키(p.89-90): CLR SOLO를 누른 채 UTILITY = 화면 캡처(USB "screens" 폴더). 켤 때 LIBRARY를 누르고 있기 = STARTUP 파일 자동 불러오기 건너뛰기.
- 녹음·재생(p.24, 82-86)
  - 앞면 USB 메모리에 2트랙·4트랙 WAV 녹음/재생: 화면 위쪽 USB 아이콘 → USB Recorder/Player. ROUTING → OUTPUTS의 RECORDER 그룹에 녹음할 신호(예: 메인 L/R)를 지정합니다. 4트랙·24비트는 SETUP → GENERAL의 USB HOST SPEED가 HS여야 합니다(p.44).
  - USB를 뺄 때는 주황색 LED가 꺼진 뒤에(p.24).
  - WING-LIVE 확장 카드: SD 카드에 최대 32/64트랙 멀티트랙 녹음.
## 13. 자주 생기는 문제 - 확인 순서 (일반 음향 지식, 설명서 내용 아님)
- 하울링(삐-):
  1) 소리 나는 쪽(메인/모니터)의 해당 채널이나 버스를 조금 내린다(2~3 dB)
  2) 마이크와 스피커 방향·거리 확인
  3) 로우컷 확인
  4) EQ의 LISTEN으로 문제 주파수를 찾아 살짝 깎는다
- 소리가 안 남: 무선 마이크 배터리·수신기 → 케이블 → 채널 뮤트 → 채널 페이더 → DCA 뮤트·페이더 → 뮤트 그룹 → 메인(또는 모니터 버스) 뮤트·페이더 → SOF가 켜져 있지 않은지 → 라우팅
- 모니터에 자기 소리가 안 들림: 해당 버스 센드 켜짐·레벨 → 버스 마스터 페이더·뮤트 → 버스 출력 라우팅(P16 등) → 개인 모니터 기기 볼륨
