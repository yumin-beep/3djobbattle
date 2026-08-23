using System.Collections;
using Photon.Pun;
using Photon.Realtime;
using UnityEngine;
using Hashtable = ExitGames.Client.Photon.Hashtable;

public enum GameState : byte { Lobby, Battle, GameOver }

/// 매치 흐름 관리: 로비(연습) → 5분 점령전 → 승자 발표 → 로비
/// 승리 조건: 제한시간 동안 중앙 스팟을 가장 오래 점령한 사람
public class GameManager : MonoBehaviourPunCallbacks
{
    public static GameManager Instance { get; private set; }

    public const string PropJob = "job";       // 플레이어 프로퍼티: 직업 (byte)
    private const string PropState = "state";  // 방 프로퍼티: 게임 상태 (byte)
    private const string PropWinner = "winner";
    private const string PropParts = "parts";  // 방 프로퍼티: 이번 라운드 참가자 (int[])
    private const string PropEndTime = "endT"; // 방 프로퍼티: 매치 종료 시각 (PhotonNetwork.Time 기준)

    public const float MatchDuration = 300f;   // 5분

    private static readonly Vector3[] SpawnPoints =
    {
        new(-12f, 1.2f, -12f),
        new(12f, 1.2f, 12f),
        new(-12f, 1.2f, 12f),
        new(12f, 1.2f, -12f),
    };

    public static Vector3 GetSpawnPoint(int actorNumber) => SpawnPoints[Mathf.Abs(actorNumber) % 4];

    private void Awake()
    {
        Instance = this;
    }

    public GameState State
    {
        get
        {
            var room = PhotonNetwork.CurrentRoom;
            if (room != null && room.CustomProperties.TryGetValue(PropState, out var v)) return (GameState)(byte)v;
            return GameState.Lobby;
        }
    }

    public string Winner
    {
        get
        {
            var room = PhotonNetwork.CurrentRoom;
            if (room != null && room.CustomProperties.TryGetValue(PropWinner, out var v)) return (string)v;
            return "";
        }
    }

    public double RemainingTime
    {
        get
        {
            var room = PhotonNetwork.CurrentRoom;
            if (room == null || !room.CustomProperties.TryGetValue(PropEndTime, out var v)) return 0;
            return System.Math.Max(0, (double)v - PhotonNetwork.Time);
        }
    }

    /// 전투 라운드 도중에 들어온 플레이어는 참가자가 아님 (다음 라운드부터 참여)
    public bool IsParticipant(int actorNumber)
    {
        var room = PhotonNetwork.CurrentRoom;
        if (room == null || !room.CustomProperties.TryGetValue(PropParts, out var v) || v is not int[] parts) return true;
        return System.Array.IndexOf(parts, actorNumber) >= 0;
    }

    public static JobType JobOf(Player player)
    {
        if (player != null && player.CustomProperties.TryGetValue(PropJob, out var v)) return (JobType)(byte)v;
        return JobType.None;
    }

    public static string DisplayName(Player player) =>
        player == null ? "?" : $"P{player.ActorNumber} {JobDatabase.Get(JobOf(player)).name}";

    /// 모든 참전자(사람+AI)의 PlayerJob 컴포넌트
    public static PlayerJob[] AllCombatants() => Object.FindObjectsByType<PlayerJob>(FindObjectsSortMode.None);

    public int BotCount
    {
        get
        {
            int n = 0;
            foreach (var pj in AllCombatants()) if (pj.IsBot) n++;
            return n;
        }
    }

    public bool CanStartMatch(out string reason)
    {
        reason = "";
        if (!PhotonNetwork.InRoom) { reason = "방에 입장하지 않았습니다"; return false; }

        foreach (var player in PhotonNetwork.PlayerList)
        {
            if (JobOf(player) == JobType.None)
            {
                reason = "모든 플레이어가 직업을 선택해야 합니다";
                return false;
            }
        }

        int total = 0;
        foreach (var pj in AllCombatants()) if (pj.Job != JobType.None) total++;
        if (total < 2)
        {
            reason = "2명 이상 필요합니다 (AI를 추가해도 됩니다)";
            return false;
        }
        return true;
    }

    /// 마스터 클라이언트만 호출
    public void StartMatch()
    {
        if (!PhotonNetwork.IsMasterClient || State == GameState.Battle) return;
        if (!CanStartMatch(out _)) return;

        var combatants = AllCombatants();
        var parts = new System.Collections.Generic.List<int>();
        foreach (var pj in combatants)
            if (pj.Job != JobType.None) parts.Add(pj.Actor);

        if (CapturePoint.Instance != null) CapturePoint.Instance.ResetAll();

        PhotonNetwork.CurrentRoom.SetCustomProperties(new Hashtable
        {
            [PropState] = (byte)GameState.Battle,
            [PropWinner] = "",
            [PropParts] = parts.ToArray(),
            [PropEndTime] = PhotonNetwork.Time + MatchDuration,
        });
    }

    // ---------- AI 봇 관리 (마스터 전용, 로비에서만) ----------

    public void AddBot()
    {
        if (!PhotonNetwork.IsMasterClient || State == GameState.Battle) return;
        if (PhotonNetwork.CurrentRoom.PlayerCount + BotCount >= 4) return;

        // 비어있는 가상 액터 번호 찾기
        int actor = 1001;
        while (PlayerJob.FindByActor(actor) != null) actor++;

        var jobs = JobDatabase.Selectable;
        var jobType = jobs[Random.Range(0, jobs.Length)];
        PhotonNetwork.InstantiateRoomObject("Player", GetSpawnPoint(actor), Quaternion.identity, 0,
            new object[] { actor, (byte)jobType });
    }

    public void RemoveBot()
    {
        if (!PhotonNetwork.IsMasterClient || State == GameState.Battle) return;
        PlayerJob last = null;
        foreach (var pj in AllCombatants())
            if (pj.IsBot && (last == null || pj.Actor > last.Actor)) last = pj;
        if (last != null) PhotonNetwork.Destroy(last.gameObject);
    }

    /// 마스터: 제한시간 만료 체크
    private void Update()
    {
        if (!PhotonNetwork.InRoom || !PhotonNetwork.IsMasterClient) return;
        if (State == GameState.Battle && RemainingTime <= 0) EndMatch();
    }

    private void EndMatch()
    {
        var cp = CapturePoint.Instance;
        PlayerJob best = null;
        float bestTime = 0f;
        foreach (var pj in AllCombatants())
        {
            float t = cp != null ? cp.GetHold(pj.Actor) : 0f;
            if (t > bestTime) { bestTime = t; best = pj; }
        }

        string winner = best == null ? "무승부" : $"{best.DisplayName} ({bestTime:F0}초 점령)";
        PhotonNetwork.CurrentRoom.SetCustomProperties(new Hashtable
        {
            [PropState] = (byte)GameState.GameOver,
            [PropWinner] = winner,
        });
        StartCoroutine(BackToLobby());
    }

    /// 상태 전환 시 각 클라이언트가 자기가 제어하는 캐릭터들을 리셋 (마스터는 AI도 함께)
    public override void OnRoomPropertiesUpdate(Hashtable changedProps)
    {
        if (!changedProps.ContainsKey(PropState)) return;
        if (State is GameState.Battle or GameState.Lobby) ResetControlledPlayers();
    }

    private void ResetControlledPlayers()
    {
        foreach (var pj in AllCombatants())
        {
            if (!pj.photonView.IsMine) continue;
            pj.GetComponent<PlayerHealth>().ReviveLocal();
            pj.GetComponent<PlayerController>().TeleportLocal(GetSpawnPoint(pj.Actor));
        }
    }

    public override void OnMasterClientSwitched(Player newMasterClient)
    {
        // 마스터가 나가면 새 마스터가 흐름을 이어받음 (전투 타이머는 Update가 처리)
        if (newMasterClient.IsLocal && State == GameState.GameOver) StartCoroutine(BackToLobby());
    }

    private IEnumerator BackToLobby()
    {
        yield return new WaitForSeconds(6f);
        if (!PhotonNetwork.IsMasterClient || State != GameState.GameOver) yield break;
        PhotonNetwork.CurrentRoom.SetCustomProperties(new Hashtable { [PropState] = (byte)GameState.Lobby });
    }
}
