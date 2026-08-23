using Photon.Pun;
using Photon.Realtime;
using UnityEngine;
using Hashtable = ExitGames.Client.Photon.Hashtable;

/// 직업과 정체성(사람=플레이어 프로퍼티, AI=인스턴스 데이터) + 색상, 피격 플래시, 사망 숨김.
/// 사람과 AI를 통합해 다루는 창구: Actor / Job / DisplayName
public class PlayerJob : MonoBehaviourPunCallbacks, IPunInstantiateMagicCallback
{
    public bool IsBot { get; private set; }

    private int botActor = -1;
    private JobType botJob = JobType.None;
    private JobType humanJob = JobType.None;

    private Renderer[] renderers;
    private PlayerHealth health;
    private Color baseColor = Color.white;
    private float flashUntil;
    private bool flashing;
    private bool deadShown;
    private int lastHp;

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
        renderers = GetComponentsInChildren<Renderer>(true);
        health = GetComponent<PlayerHealth>();
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
        ApplyColor(JobDatabase.Get(Job).color);
    }

    private void ApplyColor(Color color)
    {
        baseColor = color;
        flashing = false;
        foreach (var r in renderers) r.material.SetColor("_BaseColor", color);
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
            Color c = flash ? Color.Lerp(baseColor, Color.white, 0.85f) : baseColor;
            foreach (var r in renderers) r.material.SetColor("_BaseColor", c);
        }

        // 사망 시 숨김
        if (health.IsDead != deadShown)
        {
            deadShown = health.IsDead;
            foreach (var r in renderers) r.enabled = !deadShown;
        }
    }
}
