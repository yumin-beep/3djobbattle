# 직업대전 (Job Battle)

> 현대 직업들의 4인 멀티플레이 점령전 — Unity 3D + Photon PUN 2

## 게임 소개

빵집사장·경찰·트레이더·소방관 — 현대 직업 컨셉의 캐릭터 4명이 겨루는 개인전 점령전(King of the Hill)입니다. 맵 중앙 점령 스팟(반경 3m)에 **혼자** 3초 머무르면 점령, 5분 동안 누적 점령 시간 1위가 승리합니다. 인원이 부족하면 방장 클라이언트가 구동하는 AI 봇이 빈 자리를 채웁니다.

- **엔진**: Unity 6 (URP)
- **네트워크**: Photon PUN 2
- **상태**: 개발 진행 중 (1인 개발)

## 실행하기

이 저장소에는 Photon App ID가 포함되어 있지 않습니다. 직접 실행하려면:

1. [Photon 대시보드](https://dashboard.photonengine.com)에서 무료 PUN 앱 생성
2. `Assets/Photon/PhotonUnityNetworking/Resources/PhotonServerSettings.asset`의 `AppIdRealtime`에 발급받은 App ID 입력

## 네트워크 설계에서 한 고민

**Netcode for GameObjects에서 Photon PUN 2로 전환** — 초기엔 유니티 공식 Netcode로 시작했지만, 별도 서버 호스팅 없이 방 기반 매치를 빠르게 붙일 수 있는 PUN 2로 전환했습니다. 룸/플레이어 상태는 커스텀 프로퍼티로, HP 등 실시간 값은 `IPunObservable` 스트림으로 동기화합니다.

**소유자 판정 구조** — 명중 판정은 공격자 클라이언트에서 하되, 체력 차감은 **피해자를 소유한 클라이언트에 RPC로 위임**합니다. 자기 상태는 자기 소유자만 바꾸도록 해서, 동시 피격 시 상태가 어긋나는 문제를 구조적으로 차단했습니다.

**AI 봇의 정체성 문제** — 봇은 소유 플레이어가 없어 액터 번호가 충돌할 수 있습니다. 가상 액터 번호(1000번대)를 부여하고 `InstantiationData`로 봇 정체성을 전달해, 늦게 입장한 클라이언트도 봇을 올바르게 재구성하도록 했습니다.

## 개발 방식

프로그래밍·Unity 통합은 직접 구현하고, 3D 모델 등 아트 에셋은 생성형 AI(Blender 파이썬 스크립트 발주)로 제작한 뒤 FBX 구조·머티리얼 슬롯을 직접 검수해 통합했습니다.
