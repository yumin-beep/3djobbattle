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

## 만든 기능

- Photon으로 방 생성과 4인 접속을 구현함.
- 이동, 공격, 체력, 리스폰과 점령 기능을 구현함.
- 접속한 사람들에게 캐릭터 위치와 상태가 같이 보이도록 처리함.
- 방장이 AI 봇을 만들고 움직이도록 구현함.
- 캐릭터 모델을 만든 뒤 Unity에 넣고 동작을 직접 확인했음.

## 현재 상태

- 온라인 접속과 기본 전투, 점령은 플레이할 수 있음.
- 캐릭터별 기술과 맵, 전체 마무리는 아직 개발 중임.

## 직접 실행하기

- 공개 저장소에는 Photon App ID를 넣지 않았음.
- Unity에서 실행하려면 [Photon 대시보드](https://dashboard.photonengine.com)에서 PUN 앱을 만든 뒤 `PhotonServerSettings.asset`에 본인의 App ID를 입력해야 함.
- 위 배포 파일은 macOS용이며 서명하지 않은 개인 빌드임.
