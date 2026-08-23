using System.Collections;
using Photon.Pun;
using UnityEngine;

/// 체력 + 상태이상(스턴/슬로우/방패/버프).
/// 내 캐릭터의 상태는 내 클라이언트가 판정하고(OnPhotonSerializeView로 동기화),
/// 공격자는 SendHit()으로 피해자의 소유 클라이언트에게 피격을 전달한다.
/// 전투 중 사망하면 4초 후 자동 리스폰.
public class PlayerHealth : MonoBehaviourPun, IPunObservable
{
    public int Hp { get; private set; } = 200;
    public int MaxHp { get; private set; } = 200;
    public bool IsDead { get; private set; }
    public double RespawnAt { get; private set; }

    private double stunUntil, slowUntil, shieldUntil, buffUntil;
    private float slowFactor = 1f;

    public const float ShieldReduction = 0.4f; // 방패 중 받는 피해 40%로
    public const float BuffMultiplier = 1.5f;  // 버프 중 주는 피해 150%
    public const float RespawnDelay = 4f;

    private static double Now => PhotonNetwork.Time;

    public bool IsStunned => Now < stunUntil;
    public float CurrentSpeedMult => Now < slowUntil ? slowFactor : 1f;
    public float DamageDealtMult => Now < buffUntil ? BuffMultiplier : 1f;
    public double ShieldRemaining => System.Math.Max(0, shieldUntil - Now);
    public double BuffRemaining => System.Math.Max(0, buffUntil - Now);
    public double RespawnRemaining => System.Math.Max(0, RespawnAt - Now);

    // ---------- 공격자가 호출 ----------

    /// 피해자를 제어하는 클라이언트로 피격 전달 (AI는 룸 오브젝트라 방장이 제어)
    public void SendHit(int damage, float stun = 0f, float slowF = 1f, float slowDur = 0f)
    {
        var controller = photonView.Owner ?? PhotonNetwork.MasterClient;
        if (controller == null) return;
        photonView.RPC(nameof(RpcApplyHit), controller, damage, stun, slowF, slowDur);
    }

    [PunRPC]
    private void RpcApplyHit(int damage, float stun, float slowF, float slowDur)
    {
        if (!photonView.IsMine || IsDead) return;
        if (GetComponent<PlayerJob>().Job == JobType.None) return; // 직업 미선택 = 무적

        var gm = GameManager.Instance;
        bool inBattle = gm != null && gm.State == GameState.Battle;
        if (inBattle && !gm.IsParticipant(GetComponent<PlayerJob>().Actor)) return; // 라운드 미참가자 보호

        if (Now < shieldUntil) damage = Mathf.RoundToInt(damage * ShieldReduction);
        Hp = Mathf.Max(0, Hp - damage);
        if (stun > 0f) stunUntil = Now + stun;
        if (slowDur > 0f) { slowFactor = slowF; slowUntil = Now + slowDur; }
        if (Hp > 0) return;

        if (!inBattle)
        {
            Hp = MaxHp; // 로비 연습 중엔 즉시 회복
            return;
        }

        IsDead = true;
        RespawnAt = Now + RespawnDelay;
        StartCoroutine(RespawnRoutine());
    }

    private IEnumerator RespawnRoutine()
    {
        yield return new WaitForSeconds(RespawnDelay);
        if (!IsDead) yield break; // 이미 로비 복귀 등으로 부활함
        var gm = GameManager.Instance;
        if (gm == null || gm.State != GameState.Battle) yield break;

        ReviveLocal();
        GetComponent<PlayerController>().TeleportLocal(GameManager.GetSpawnPoint(GetComponent<PlayerJob>().Actor));
    }

    // ---------- 소유자 로컬 조작 ----------

    public void LocalSetMaxHp(int max)
    {
        if (!photonView.IsMine) return;
        MaxHp = max;
        Hp = max;
    }

    /// 스킬 비용 등 자해 피해 (죽지는 않음)
    public void LocalSelfCost(int amount)
    {
        if (photonView.IsMine && !IsDead) Hp = Mathf.Max(1, Hp - amount);
    }

    public void LocalHeal(int amount)
    {
        if (photonView.IsMine && !IsDead) Hp = Mathf.Min(MaxHp, Hp + amount);
    }

    public void LocalShield(float duration) { if (photonView.IsMine) shieldUntil = Now + duration; }
    public void LocalBuff(float duration) { if (photonView.IsMine) buffUntil = Now + duration; }

    public void ReviveLocal()
    {
        if (!photonView.IsMine) return;
        IsDead = false;
        Hp = MaxHp;
        stunUntil = slowUntil = shieldUntil = buffUntil = 0;
        slowFactor = 1f;
    }

    // ---------- 동기화 ----------

    public void OnPhotonSerializeView(PhotonStream stream, PhotonMessageInfo info)
    {
        if (stream.IsWriting)
        {
            stream.SendNext(Hp);
            stream.SendNext(MaxHp);
            stream.SendNext(IsDead);
            stream.SendNext(stunUntil);
            stream.SendNext(slowUntil);
            stream.SendNext(slowFactor);
            stream.SendNext(shieldUntil);
            stream.SendNext(buffUntil);
        }
        else
        {
            Hp = (int)stream.ReceiveNext();
            MaxHp = (int)stream.ReceiveNext();
            IsDead = (bool)stream.ReceiveNext();
            stunUntil = (double)stream.ReceiveNext();
            slowUntil = (double)stream.ReceiveNext();
            slowFactor = (float)stream.ReceiveNext();
            shieldUntil = (double)stream.ReceiveNext();
            buffUntil = (double)stream.ReceiveNext();
        }
    }
}
