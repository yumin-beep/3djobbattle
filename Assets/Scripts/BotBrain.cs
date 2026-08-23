using Photon.Pun;
using UnityEngine;

/// 마스터 클라이언트에서 동작하는 AI. 점령 스팟을 우선하고, 근처의 적과 교전한다.
/// PlayerController가 MoveInput/AimDir를 읽어가고, 공격은 PlayerCombat.BotUse로 실행.
public class BotBrain : MonoBehaviourPun
{
    public Vector2 MoveInput { get; private set; }
    public Vector3 AimDir { get; private set; } = Vector3.forward;

    private PlayerJob job;
    private PlayerHealth health;
    private PlayerCombat combat;

    private float decisionCooldown;   // 스킬 사용 판단 주기 (사람같은 반응속도)
    private float strafeTimer;
    private int strafeSign = 1;
    private Vector3 lastPos;
    private float stuckTime;
    private float unstickTimer;
    private Vector3 unstickDir;

    private void Awake()
    {
        job = GetComponent<PlayerJob>();
        health = GetComponent<PlayerHealth>();
        combat = GetComponent<PlayerCombat>();
    }

    private bool IsMelee => job.Job is JobType.Baker or JobType.Firefighter;
    private float WeaponRange => IsMelee ? 2.3f : 9f;

    private bool Ready(int slot) => Time.time >= combat.LocalReadyTime[slot];

    private void Update()
    {
        MoveInput = Vector2.zero;
        if (!photonView.IsMine || !job.IsBot || health.IsDead || health.IsStunned) return;

        decisionCooldown -= Time.deltaTime;
        strafeTimer -= Time.deltaTime;
        if (strafeTimer <= 0f)
        {
            strafeTimer = Random.Range(0.8f, 1.8f);
            strafeSign = Random.value < 0.5f ? -1 : 1;
        }

        var cp = CapturePoint.Instance;
        var enemy = FindNearestEnemy();
        bool wantPoint = cp != null && cp.OwnerActor != job.Actor;

        // 스팟을 노리는데 적이 스팟 근처에 있으면 그 적부터 처리 (혼자 서야 점령되니까)
        bool padContested = wantPoint && enemy != null && cp != null &&
            HorizontalDist(enemy.transform.position, cp.transform.position) < CapturePoint.Radius + 1.5f;

        if (enemy != null && (padContested ||
            HorizontalDist(transform.position, enemy.transform.position) < (wantPoint ? WeaponRange : 12f)))
        {
            Fight(enemy);
        }
        else if (wantPoint && cp != null)
        {
            MoveTowards(cp.transform.position, 0.4f);
            if (enemy != null) TryAttack(enemy); // 이동 중 기회 공격
        }
        else if (cp != null)
        {
            Guard(cp.transform.position, enemy);
        }

        ApplyUnstick();
    }

    private void Fight(PlayerHealth enemy)
    {
        Vector3 toEnemy = enemy.transform.position - transform.position;
        toEnemy.y = 0f;
        float dist = toEnemy.magnitude;
        Vector3 dir = toEnemy.normalized;
        AimDir = dir;

        float desired = IsMelee ? 1.6f : 6.5f;
        Vector3 move = Vector3.zero;
        if (dist > desired) move = dir;
        else if (dist < desired * 0.6f) move = -dir;
        move += Vector3.Cross(Vector3.up, dir) * (0.6f * strafeSign); // 옆 무빙

        SetMove(move);
        TryAttack(enemy);
    }

    private void Guard(Vector3 padPos, PlayerHealth enemy)
    {
        Vector3 toPad = padPos - transform.position;
        toPad.y = 0f;

        if (toPad.magnitude > 4.5f) SetMove(toPad.normalized);
        else SetMove(Vector3.Cross(Vector3.up, toPad.normalized) * strafeSign * 0.5f); // 스팟 주변 배회

        if (enemy != null)
        {
            Vector3 toEnemy = enemy.transform.position - transform.position;
            toEnemy.y = 0f;
            AimDir = toEnemy.normalized;
            if (toEnemy.magnitude < WeaponRange + 1f) TryAttack(enemy);
        }
        else if (toPad.sqrMagnitude > 0.01f)
        {
            AimDir = toPad.normalized;
        }
    }

    private void MoveTowards(Vector3 dest, float stopDist)
    {
        Vector3 to = dest - transform.position;
        to.y = 0f;
        if (to.magnitude <= stopDist)
        {
            SetMove(Vector3.zero);
            return;
        }
        SetMove(to.normalized);
        AimDir = to.normalized;
    }

    private void TryAttack(PlayerHealth enemy)
    {
        if (decisionCooldown > 0f) return;

        Vector3 toEnemy = enemy.transform.position - transform.position;
        toEnemy.y = 0f;
        float dist = toEnemy.magnitude;
        Vector3 dir = toEnemy.normalized;
        bool used = false;

        switch (job.Job)
        {
            case JobType.Baker:
                if (health.Hp < health.MaxHp * 0.45f && Ready(2)) { combat.BotUse(2, dir); used = true; }
                else if (dist < 8f && Ready(1)) { combat.BotUse(1, dir); used = true; }
                else if (dist < 2.3f) { combat.BotUse(0, dir); used = true; }
                break;

            case JobType.Police:
                if (health.Hp < health.MaxHp * 0.4f && Ready(2)) { combat.BotUse(2, dir); used = true; }
                else if (dist < 7f && Ready(1)) { combat.BotUse(1, dir); used = true; }
                else if (dist < 9.5f) { combat.BotUse(0, dir); used = true; }
                break;

            case JobType.Trader:
                if (dist < 9f && Ready(2)) { combat.BotUse(2, dir); used = true; }
                else if (dist < 9f && Ready(1) && health.Hp > health.MaxHp * 0.35f) { combat.BotUse(1, dir); used = true; }
                else if (dist < 10f) { combat.BotUse(0, dir); used = true; }
                break;

            case JobType.Firefighter:
                if (dist < 2.5f) { combat.BotUse(0, dir); used = true; }
                else if (dist < 5.5f && Ready(1)) { combat.BotUse(1, dir); used = true; }
                else if (dist > 3f && dist < 11f && Ready(2)) { combat.BotUse(2, dir); used = true; }
                break;
        }

        if (used) decisionCooldown = Random.Range(0.25f, 0.55f);
    }

    private PlayerHealth FindNearestEnemy()
    {
        var gm = GameManager.Instance;
        bool battle = gm != null && gm.State == GameState.Battle;

        PlayerHealth nearest = null;
        float best = float.MaxValue;
        foreach (var other in FindObjectsByType<PlayerHealth>(FindObjectsSortMode.None))
        {
            if (other.gameObject == gameObject || other.IsDead) continue;
            var pj = other.GetComponent<PlayerJob>();
            if (pj.Job == JobType.None) continue;
            if (battle && gm != null && !gm.IsParticipant(pj.Actor)) continue;

            float d = HorizontalDist(transform.position, other.transform.position);
            if (d < best) { best = d; nearest = other; }
        }
        return nearest;
    }

    private void SetMove(Vector3 dir)
    {
        dir.y = 0f;
        if (dir.sqrMagnitude > 1f) dir.Normalize();
        MoveInput = new Vector2(dir.x, dir.z);
    }

    /// 장애물에 낑겼을 때 옆으로 비켜가기
    private void ApplyUnstick()
    {
        if (unstickTimer > 0f)
        {
            unstickTimer -= Time.deltaTime;
            SetMove(unstickDir);
            return;
        }

        bool wantsToMove = MoveInput.sqrMagnitude > 0.01f;
        float moved = (transform.position - lastPos).magnitude;
        lastPos = transform.position;

        if (wantsToMove && moved < 0.01f) stuckTime += Time.deltaTime;
        else stuckTime = 0f;

        if (stuckTime > 1f)
        {
            stuckTime = 0f;
            unstickTimer = 0.7f;
            Vector3 current = new(MoveInput.x, 0f, MoveInput.y);
            unstickDir = Quaternion.Euler(0f, Random.value < 0.5f ? 90f : -90f, 0f) * current;
        }
    }

    private static float HorizontalDist(Vector3 a, Vector3 b)
    {
        a.y = 0f;
        b.y = 0f;
        return Vector3.Distance(a, b);
    }
}
