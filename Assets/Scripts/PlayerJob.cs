using System.Collections.Generic;
using Photon.Pun;
using Photon.Realtime;
using UnityEngine;
using Hashtable = ExitGames.Client.Photon.Hashtable;

/// 직업과 정체성(사람=플레이어 프로퍼티, AI=인스턴스 데이터) + 비주얼 전환, 피격 플래시, 사망 숨김.
/// 캐릭터 모델이 있는 직업(현재 빵집사장=고양이)은 모델을, 나머지는 직업 색 캡슐을 보여준다.
public class PlayerJob : MonoBehaviourPunCallbacks, IPunInstantiateMagicCallback
{
    public bool IsBot { get; private set; }

    private int botActor = -1;
    private JobType botJob = JobType.None;
    private JobType humanJob = JobType.None;

    private GameObject capsuleVisual;   // 자식 "Visual_Capsule" (기본)
    private GameObject bakerCatVisual;  // 자식 "Visual_BakerCat" (빵집사장 모델)
    private Renderer[] activeRenderers = System.Array.Empty<Renderer>();
    private readonly Dictionary<Renderer, Color> baseColors = new();

    private PlayerHealth health;
    private float flashUntil;
    private bool flashing;
    private bool deadShown;
    private int lastHp;

    private static readonly Color FlashColor = new(1f, 0.3f, 0.25f);

    /// 사람은 Photon 액터 번호, AI는 1000번대 가상 번호
    public int Actor => IsBot ? botActor : (photonView.Owner != null ? photonView.Owner.ActorNumber : -1);
    public JobType Job => IsBot ? botJob : humanJob;
    public string DisplayName => IsBot ? $"AI {JobDatabase.Get(botJob).name}" : GameManager.DisplayName(photonView.Owner);

    /// actor 번호로 참전자(사람+AI) 찾기
    public static PlayerJob FindByActor(int actor)
    {
        if (actor < 0) return null;
        foreach (var pj in FindObjectsByType<PlayerJob>(FindObjectsSortMode.None))
            if (pj.Actor == actor) return pj;
        return null;
    }

    private void Awake()
    {
        health = GetComponent<PlayerHealth>();
        var capsule = transform.Find("Visual_Capsule");
        capsuleVisual = capsule != null ? capsule.gameObject : null;
        var cat = transform.Find("Visual_BakerCat");
        bakerCatVisual = cat != null ? cat.gameObject : null;
    }

    public void OnPhotonInstantiate(PhotonMessageInfo info)
    {
        // AI는 생성 데이터로 정체성을 받음: { 가상 액터 번호(int, 1000+), 직업(byte) }
        var data = photonView.InstantiationData;
        if (data != null && data.Length >= 2 && data[0] is int actor && actor >= 1000)
        {
            IsBot = true;
            botActor = actor;
            botJob = (JobType)(byte)data[1];
            if (photonView.IsMine) health.LocalSetMaxHp(JobDatabase.Get(botJob).maxHp);
        }
        Refresh();
    }

    private void Start()
    {
        lastHp = health.Hp;
        Refresh();
    }

    /// 로컬 사람 플레이어 전용 (직업 선택 UI에서 호출)
    public void SelectJob(JobType type)
    {
        if (IsBot || !photonView.IsMine || type == JobType.None) return;
        if (GameManager.Instance != null && GameManager.Instance.State == GameState.Battle) return;

        health.LocalSetMaxHp(JobDatabase.Get(type).maxHp);
        PhotonNetwork.LocalPlayer.SetCustomProperties(new Hashtable { [GameManager.PropJob] = (byte)type });
    }

    /// 로비에서 직업 선택 화면으로 돌아가기
    public void ResetJob()
    {
        if (IsBot || !photonView.IsMine) return;
        if (GameManager.Instance != null && GameManager.Instance.State == GameState.Battle) return;
        PhotonNetwork.LocalPlayer.SetCustomProperties(new Hashtable { [GameManager.PropJob] = (byte)JobType.None });
    }

    public override void OnPlayerPropertiesUpdate(Player targetPlayer, Hashtable changedProps)
    {
        if (!IsBot && targetPlayer != null && targetPlayer == photonView.Owner && changedProps.ContainsKey(GameManager.PropJob))
            Refresh();
    }

    private void Refresh()
    {
        if (!IsBot) humanJob = GameManager.JobOf(photonView.Owner);
        ApplyVisual();
    }

    /// 직업에 맞는 비주얼 선택 + 색/렌더러 목록 재구성
    private void ApplyVisual()
    {
        bool useCat = Job == JobType.Baker && bakerCatVisual != null;
        if (bakerCatVisual != null) bakerCatVisual.SetActive(useCat);
        if (capsuleVisual != null) capsuleVisual.SetActive(!useCat);

        GameObject visualRoot = useCat ? bakerCatVisual : capsuleVisual;
        if (visualRoot == null) visualRoot = gameObject; // 구버전 프리팹 호환

        baseColors.Clear();
        activeRenderers = visualRoot.GetComponentsInChildren<Renderer>(true);
        Color jobColor = JobDatabase.Get(Job).color;
        bool dead = health != null && health.IsDead;

        foreach (var r in activeRenderers)
        {
            if (useCat)
            {
                // 모델은 자기 텍스처 색 유지
                baseColors[r] = r.material.GetColor("_BaseColor");
            }
            else
            {
                r.material.SetColor("_BaseColor", jobColor);
                baseColors[r] = jobColor;
            }
            r.enabled = !dead;
        }

        flashing = false;
        deadShown = dead;

        var pa = GetComponent<PlayerAnimator>();
        if (pa != null) pa.RefreshAnimator();
    }

    private void Update()
    {
        // 피격 플래시: HP 감소 감지
        if (health.Hp < lastHp) flashUntil = Time.time + 0.15f;
        lastHp = health.Hp;

        bool flash = Time.time < flashUntil;
        if (flash != flashing)
        {
            flashing = flash;
            foreach (var r in activeRenderers)
            {
                if (r == null) continue;
                Color c = flash ? Color.Lerp(baseColors[r], FlashColor, 0.7f) : baseColors[r];
                r.material.SetColor("_BaseColor", c);
            }
        }

        // 사망 시 숨김
        if (health.IsDead != deadShown)
        {
            deadShown = health.IsDead;
            foreach (var r in activeRenderers)
                if (r != null) r.enabled = !deadShown;
        }
    }
}
