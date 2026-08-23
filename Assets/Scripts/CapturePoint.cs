using System.Collections.Generic;
using Photon.Pun;
using Photon.Realtime;
using UnityEngine;

/// 중앙 점령 스팟. 혼자서 3초간 서 있으면 점령(빼앗기도 동일 조건).
/// 판정은 방장(룸 오브젝트 소유자)이 하고 결과를 스트림으로 동기화한다.
public class CapturePoint : MonoBehaviourPun, IPunObservable
{
    public static CapturePoint Instance { get; private set; }

    public const float Radius = 3f;
    public const float CaptureTime = 3f;

    public int OwnerActor { get; private set; } = -1;   // 현재 점령자 (없으면 -1)
    public int CaptureActor { get; private set; } = -1; // 점령 시도 중인 플레이어
    public float Progress { get; private set; }

    private readonly Dictionary<int, float> holdTimes = new(); // actor → 누적 점령 시간(초)

    private Renderer padRenderer;
    private static readonly Color NeutralColor = new(0.5f, 0.5f, 0.55f);

    private void Awake()
    {
        Instance = this;
        padRenderer = GetComponentInChildren<Renderer>();
    }

    private void OnDestroy()
    {
        if (Instance == this) Instance = null;
    }

    public float GetHold(int actor) => holdTimes.TryGetValue(actor, out var t) ? t : 0f;

    /// 방장 전용: 매치 시작 시 초기화
    public void ResetAll()
    {
        if (!photonView.IsMine) return;
        OwnerActor = -1;
        CaptureActor = -1;
        Progress = 0f;
        holdTimes.Clear();
    }

    private void Update()
    {
        if (photonView.IsMine) Simulate(Time.deltaTime);
        UpdateVisual();
    }

    private void Simulate(float dt)
    {
        var gm = GameManager.Instance;
        bool battle = gm != null && gm.State == GameState.Battle;

        // 스팟 위의 (살아있는, 직업 선택한) 플레이어/AI 집계
        var occupants = new List<int>();
        foreach (var ph in FindObjectsByType<PlayerHealth>(FindObjectsSortMode.None))
        {
            if (ph.IsDead) continue;
            var pj = ph.GetComponent<PlayerJob>();
            if (pj.Job == JobType.None) continue;
            int actor = pj.Actor;
            if (battle && gm != null && !gm.IsParticipant(actor)) continue;
            Vector3 d = ph.transform.position - transform.position;
            d.y = 0f;
            if (d.magnitude <= Radius) occupants.Add(actor);
        }

        // 혼자 서 있을 때만 점령 진행 (이미 자기 소유면 진행 불필요)
        if (occupants.Count == 1 && occupants[0] != OwnerActor)
        {
            if (CaptureActor != occupants[0])
            {
                CaptureActor = occupants[0];
                Progress = 0f;
            }
            Progress += dt;
            if (Progress >= CaptureTime)
            {
                OwnerActor = CaptureActor;
                CaptureActor = -1;
                Progress = 0f;
                photonView.RPC(nameof(RpcCapturedFx), RpcTarget.All, OwnerActor);
            }
        }
        else
        {
            CaptureActor = -1;
            Progress = 0f;
        }

        // 점령자가 방을 나가면(또는 AI가 제거되면) 소유권 해제
        if (OwnerActor != -1 && PlayerJob.FindByActor(OwnerActor) == null) OwnerActor = -1;

        // 전투 중에만 점령 시간 누적 (스팟에서 내려와도 뺏기기 전까지 계속 쌓임)
        if (battle && OwnerActor != -1)
            holdTimes[OwnerActor] = GetHold(OwnerActor) + dt;
    }

    [PunRPC]
    private void RpcCapturedFx(int actor)
    {
        var pj = PlayerJob.FindByActor(actor);
        Color c = JobDatabase.Get(pj != null ? pj.Job : JobType.None).color;
        HitPuff.Create(transform.position + Vector3.up * 0.5f, Radius, c, 0.4f);
    }

    private void UpdateVisual()
    {
        if (padRenderer == null) return;

        var owner = PlayerJob.FindByActor(OwnerActor);
        Color color = owner != null ? JobDatabase.Get(owner.Job).color : NeutralColor;

        // 점령 시도 중이면 도전자 색으로 깜빡임
        var capturing = PlayerJob.FindByActor(CaptureActor);
        if (capturing != null)
        {
            Color cc = JobDatabase.Get(capturing.Job).color;
            color = Color.Lerp(color, cc, Mathf.PingPong(Time.time * 3f, 1f));
        }

        padRenderer.material.SetColor("_BaseColor", color);
    }

    public void OnPhotonSerializeView(PhotonStream stream, PhotonMessageInfo info)
    {
        if (stream.IsWriting)
        {
            stream.SendNext(OwnerActor);
            stream.SendNext(CaptureActor);
            stream.SendNext(Progress);
            var actors = new int[holdTimes.Count];
            var times = new float[holdTimes.Count];
            int i = 0;
            foreach (var kv in holdTimes) { actors[i] = kv.Key; times[i] = kv.Value; i++; }
            stream.SendNext(actors);
            stream.SendNext(times);
        }
        else
        {
            OwnerActor = (int)stream.ReceiveNext();
            CaptureActor = (int)stream.ReceiveNext();
            Progress = (float)stream.ReceiveNext();
            var actors = (int[])stream.ReceiveNext();
            var times = (float[])stream.ReceiveNext();
            holdTimes.Clear();
            for (int i = 0; i < actors.Length; i++) holdTimes[actors[i]] = times[i];
        }
    }
}
