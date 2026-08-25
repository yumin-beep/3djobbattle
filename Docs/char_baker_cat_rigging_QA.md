# char_baker_cat 리깅·애니메이션 검수 보고

- 작업 원본: `Art/Models/char_baker_cat_round_xy_v12.blend`
- 리깅 원본: `Art/Models/char_baker_cat_rigged.blend`
- Unity 납품 FBX: `Art/Models/char_baker_cat_rigged.fbx`
- FPS: 30
- 재임포트 높이: 1.600m
- 발바닥 최저점: Z=0.000m

## 본 구조

발주서에 실제로 이름이 명시된 7개 본을 구현했다. 발주서의 “총 8개” 표기는 아래 명시 구조 및 스키닝 지시와 산술상 불일치한다.

```text
root
└─ body
   ├─ arm.L
   ├─ arm.R
   │  └─ prop
   ├─ leg.L
   └─ leg.R
```

## 리지드 바인딩

- 모든 납품 메시 파츠는 담당 버텍스 그룹 하나에 1.0으로 할당했다.
- 자동 웨이트와 부드러운 혼합 웨이트를 사용하지 않았다.
- 누락 또는 1.0이 아닌 버텍스: 0개.
- 사용자 확정 귀 형태는 원본의 최종 위치·회전·스케일을 균일 미터 변환하여 그대로 보존했다.

## 장면·머티리얼 정리

- `BC3_Hat_Puff`: `BC3_Mat_Warm_White` 할당 확인.
- `MAT_char_baker_cat_palette` 사용 구세대 메시: 0개.
- 이름에 `Ground`가 포함된 오브젝트: 0개.
- 구세대 팔레트 및 Ground 전용 고아 메시·머티리얼을 지정 삭제했다.
- `Art/Models`에는 재생성용 v12 원본과 최종 `.blend`·`.fbx`만 보존했다.

## 액션

- `Idle`: 1–45프레임, 루프 첫/끝 동일.
- `Run`: 1–18프레임, 루프 첫/끝 동일.
- `Attack`: 1–12프레임. 바게트를 어깨 쪽 사선으로 당긴 뒤 반대편 아래 사선까지 방망이·검격처럼 휘두르고, 12프레임에 기본 자세로 복귀한다.
- `Defend`: 1–12프레임. 기존 Attack의 세로 방어와 가로 방어 동작을 별도 액션으로 이전하고, 12프레임에 기본 자세로 복귀한다.
- 렌더 픽셀 비교: Idle 1=45, Run 1=18, Attack 12=Idle 1, Defend 12=Idle 1.
- Blender 원본의 `root` 본 키프레임: 0개.

## FBX 재임포트

- 아마추어: 1개.
- 본 이름과 계층: 정상.
- AnimStack 내부 이름: `Idle`, `Run`, `Attack`, `Defend`.
- Blender 재임포트 액션 표시는 importer 규칙에 따라 `BakerCat_Rig|Idle` 형식으로 보인다.
- FBX exporter/importer가 각 스택에 생성하는 root 채널은 위치 0, 회전 identity, 스케일 1의 상수값이다. 변화량과 root motion은 0이다.
- FBX 재임포트에서 `BC3_Hat_Puff`의 `BC3_Mat_Warm_White`와 Ground/구세대 팔레트 오브젝트 부재를 재확인했다.

## 프리뷰

- `Art/Animations/char_baker_cat_idle.gif`
- `Art/Animations/char_baker_cat_run.gif`
- `Art/Animations/char_baker_cat_attack.gif`
- `Art/Animations/char_baker_cat_defend.gif`
- 전체 연속 PNG 프레임은 `Art/Animations/Idle`, `Run`, `Attack`, `Defend`에 저장했다.
