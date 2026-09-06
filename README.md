# 직업대전 (Job Battle)

![직업대전 대표 이미지](Docs/images/job-battle-cover.jpg)

현대 직업 캐릭터들이 싸우는 4인 점령전 게임을 만들었음.

- 기간: 2026.08.01 ~ 2026.09.04
- 인원: 1명
- 사용 기술: Unity 6, C#, Photon PUN 2
- 현재 상태: 핵심 기능을 구현한 프로토타입임

[macOS 프로토타입 받기](https://github.com/yumin-beep/3djobbattle/releases/tag/v0.1.0-prototype)

## 게임 설명

- 빵집 사장, 경찰, 트레이더, 소방관 중 하나를 골라 플레이함.
- 맵 중앙을 혼자 3초 동안 지키면 점령할 수 있음.
- 5분 동안 점령 시간을 가장 많이 쌓은 사람이 이기는 방식임.
- 사람이 부족하면 AI 봇이 빈자리를 채움.

![직업대전 프로토타입 실행 화면](Docs/images/job-battle-prototype.png)

## 만든 기능과 구현 방식

- Photon PUN 2로 방 생성과 4인 접속을 구현함.
- 방 상태와 직업 선택은 Photon의 `Custom Properties`로 관리했음.
- 공격자가 명중을 확인하면 피해자 쪽으로 `RPC`를 보내 HP와 상태이상을 계산하게 했음.
- HP, 사망과 버프 상태는 `IPunObservable`로 다른 접속자에게 동기화했음.
- `CapturePoint`에서 한 명만 들어와 있는지 확인하고 3초 점령 시간과 점수를 관리했음.
- 방장 클라이언트에서 `BotBrain`을 실행해 AI가 점령지와 가까운 적을 판단하게 했음.
- 캐릭터 모델을 만든 뒤 Unity에 넣고 동작을 직접 확인했음.

## 현재 상태

- 온라인 접속과 기본 전투, 점령은 플레이할 수 있음.
- 캐릭터별 기술과 맵, 전체 마무리는 아직 개발 중임.

## 직접 실행하기

- 공개 저장소에는 Photon App ID를 넣지 않았음.
- Unity에서 실행하려면 [Photon 대시보드](https://dashboard.photonengine.com)에서 PUN 앱을 만든 뒤 `PhotonServerSettings.asset`에 본인의 App ID를 입력해야 함.
- 위 배포 파일은 macOS용이며 서명하지 않은 개인 빌드임.
