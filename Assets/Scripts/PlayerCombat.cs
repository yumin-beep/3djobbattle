using System.Collections;
using System.Collections.Generic;
using Photon.Pun;
using UnityEngine;
using UnityEngine.InputSystem;

/// 공격/스킬. 입력과 명중 판정은 공격자 클라이언트에서 하고,
/// 피해 적용은 피해자의 소유 클라이언트로 RPC 전달. 좌클릭=기본, Q=스킬1, E=스킬2
public class PlayerCombat : MonoBehaviourPun
{
    [SerializeField] private GameObject projectilePrefab;

    private PlayerHealth health;
    private PlayerJob job;
    private PlayerController ctrl;

    public readonly float[] LocalReadyTime = new float[3]; // HUD 쿨다운 표시 겸 쿨다운 관리

    private static int projectileCounter;

    private static readonly Color FlourColor = new(0.98f, 0.96f, 0.9f);
    private static readonly Color BulletColor = new(0.25f, 0.25f, 0.3f);
    private static readonly Color TaserColor = new(0.3f, 0.95f, 1f);
    private static readonly Color CoinColor = new(1f, 0.85f, 0.2f);
    private static readonly Color WaterColor = new(0.35f, 0.65f, 1f);
    private static readonly Color HealColor = new(0.4f, 1f, 0.5f);

    private void Awake()
    {
        health = GetComponent<PlayerHealth>();
        job = GetComponent<PlayerJob>();
        ctrl = GetComponent<PlayerController>();
    }

    private bool CanAct
    {
        get
        {
            if (!photonView.IsMine || job.Job == JobType.None) return false;
            if (health.IsDead || health.IsStunned) return false;
            var gm = GameManager.Instance;
            if (gm != null)
            {
                if (gm.State == GameState.GameOver) return false;
                if (gm.State == GameState.Battle && !gm.IsParticipant(job.Actor)) return false;
            }
            return true;
        }
    }

    private void Update()
    {
        if (!CanAct || job.IsBot) return; // AI는 BotBrain이 BotUse로 조작

        var mouse = Mouse.current;
        var kb = Keyboard.current;
        if (mouse != null && mouse.leftButton.isPressed) TryUse(0);
        if (kb != null && kb.qKey.wasPressedThisFrame) TryUse(1);
        if (kb != null && kb.eKey.wasPressedThisFrame) TryUse(2);
    }

    private void TryUse(int slot)
    {
        if (Time.time < LocalReadyTime[slot]) return;
        LocalReadyTime[slot] = Time.time + JobDatabase.Get(job.Job).cooldowns[slot];

        Vector3 dir = ctrl.AimDirection;
        dir.y = 0f;
        dir = dir.sqrMagnitude < 0.001f ? transform.forward : dir.normalized;
        Execute(slot, dir);
    }

    /// AI(BotBrain, 마스터에서만) 전용 스킬 사용
    public void BotUse(int slot, Vector3 dir)
    {
        if (!job.IsBot || !CanAct) return;
        if (Time.time < LocalReadyTime[slot]) return;
        LocalReadyTime[slot] = Time.time + JobDatabase.Get(job.Job).cooldowns[slot];

        dir.y = 0f;
        dir = dir.sqrMagnitude < 0.001f ? transform.forward : dir.normalized;
        Execute(slot, dir);
    }

    private void Execute(int slot, Vector3 dir)
    {
        switch (job.Job)
        {
            case JobType.Baker:
                if (slot == 0) Melee(dir, 25, 2.4f, 110f);
                else if (slot == 1) FireProjectile(dir, 14f, 1.2f, 15, 0.5f, FlourColor, aoeRadius: 3.5f, slowF: 0.5f, slowDur: 3f);
                else { health.LocalHeal(60); SelfFx(HealColor); }
                break;

            case JobType.Police:
                if (slot == 0) FireProjectile(dir, 26f, 1.1f, 16, 0.25f, BulletColor);
                else if (slot == 1) FireProjectile(dir, 20f, 0.55f, 10, 0.32f, TaserColor, stun: 1.5f);
                else { health.LocalShield(3f); SelfFx(new Color(0.5f, 0.7f, 1f)); }
                break;

            case JobType.Trader:
                if (slot == 0) FireProjectile(dir, 24f, 1f, 13, 0.3f, CoinColor);
                else if (slot == 1) { health.LocalSelfCost(20); FireProjectile(dir, 18f, 1.4f, 50, 0.7f, CoinColor); }
                else { health.LocalBuff(4f); SelfFx(CoinColor); }
                break;

            case JobType.Firefighter:
                if (slot == 0) Melee(dir, 30, 2.6f, 100f);
                else if (slot == 1) WaterCone(dir, 15, 6f, 60f, 11f);
                else { ctrl.StartDash(dir); StartCoroutine(DashDamage(20)); }
                break;
        }
    }

    // ---------- 판정 (공격자 클라이언트) ----------

    private int Scaled(int baseDamage) => Mathf.RoundToInt(baseDamage * health.DamageDealtMult);

    private IEnumerable<PlayerHealth> Targets()
    {
        foreach (var other in FindObjectsByType<PlayerHealth>(FindObjectsSortMode.None))
        {
            if (other.gameObject == gameObject || other.IsDead) continue;
            yield return other;
        }
    }

    private void Melee(Vector3 dir, int damage, float range, float angle)
    {
        int dmg = Scaled(damage);
        foreach (var target in Targets())
        {
            Vector3 to = target.transform.position - transform.position;
            to.y = 0f;
            if (to.magnitude > range) continue;
            if (Vector3.Angle(dir, to) > angle * 0.5f) continue;
            target.SendHit(dmg);
        }
        Vector3 fxPos = transform.position + Vector3.up + dir * 1.5f;
        photonView.RPC(nameof(RpcMeleeFx), RpcTarget.All, fxPos, ToV3(JobDatabase.Get(job.Job).color));
    }

    private void FireProjectile(Vector3 dir, float speed, float life, int damage, float scale, Color color,
        float stun = 0f, float slowF = 1f, float slowDur = 0f, float aoeRadius = 0f)
    {
        long key = ((long)job.Actor << 32) | (uint)projectileCounter++;
        Vector3 origin = transform.position + Vector3.up * 1.2f + dir * 0.8f;

        var go = Instantiate(projectilePrefab, origin, Quaternion.LookRotation(dir));
        var p = go.GetComponent<Projectile>();
        p.InitVisual(key, dir, speed, life, scale, color);
        p.InitSim(this, Scaled(damage), stun, slowF, slowDur, aoeRadius);

        photonView.RPC(nameof(RpcProjectileFx), RpcTarget.Others, key, origin, dir, speed, life, scale, ToV3(color));
    }

    private void WaterCone(Vector3 dir, int damage, float range, float angle, float knockback)
    {
        int dmg = Scaled(damage);
        foreach (var target in Targets())
        {
            Vector3 to = target.transform.position - transform.position;
            to.y = 0f;
            if (to.magnitude > range) continue;
            if (Vector3.Angle(dir, to) > angle * 0.5f) continue;
            target.SendHit(dmg);
            var pc = target.GetComponent<PlayerController>();
            if (pc != null) pc.SendKnockback((to.normalized + Vector3.up * 0.3f) * knockback);
        }
        photonView.RPC(nameof(RpcBeamFx), RpcTarget.All, transform.position + Vector3.up, dir, range, ToV3(WaterColor));
    }

    private IEnumerator DashDamage(int damage)
    {
        int dmg = Scaled(damage);
        var hit = new HashSet<PlayerHealth>();
        float t = 0f;
        while (t < 0.45f)
        {
            foreach (var target in Targets())
            {
                if (hit.Contains(target)) continue;
                Vector3 to = target.transform.position - transform.position;
                to.y = 0f;
                if (to.magnitude > 1.8f) continue;
                hit.Add(target);
                target.SendHit(dmg);
                var pc = target.GetComponent<PlayerController>();
                if (pc != null) pc.SendKnockback(to.normalized * 8f);
            }
            t += Time.deltaTime;
            yield return null;
        }
    }

    private void SelfFx(Color color)
    {
        photonView.RPC(nameof(RpcSelfFx), RpcTarget.All, ToV3(color));
    }

    /// 투사체가 명중했을 때 (쏜 사람 클라이언트에서 호출)
    public void BroadcastProjectileHit(long key, Vector3 pos, float radius, Color color)
    {
        HitPuff.Create(pos, radius, color);
        photonView.RPC(nameof(RpcProjectileHitFx), RpcTarget.Others, key, pos, radius, ToV3(color));
    }

    // ---------- 이펙트 RPC ----------

    [PunRPC]
    private void RpcProjectileFx(long key, Vector3 origin, Vector3 dir, float speed, float life, float scale, Vector3 colorV)
    {
        var go = Instantiate(projectilePrefab, origin, Quaternion.LookRotation(dir));
        go.GetComponent<Projectile>().InitVisual(key, dir, speed, life, scale, FromV3(colorV));
    }

    [PunRPC]
    private void RpcProjectileHitFx(long key, Vector3 pos, float radius, Vector3 colorV)
    {
        Projectile.DestroyVisual(key);
        HitPuff.Create(pos, radius, FromV3(colorV));
    }

    [PunRPC]
    private void RpcMeleeFx(Vector3 pos, Vector3 colorV) => HitPuff.Create(pos, 1.1f, FromV3(colorV), 0.18f);

    [PunRPC]
    private void RpcBeamFx(Vector3 pos, Vector3 dir, float length, Vector3 colorV) => HitPuff.CreateBeam(pos, dir, length, FromV3(colorV));

    [PunRPC]
    private void RpcSelfFx(Vector3 colorV) => HitPuff.Create(transform.position + Vector3.up, 1.6f, FromV3(colorV), 0.35f);

    // Photon RPC는 Color를 직접 못 보내므로 Vector3로 변환
    private static Vector3 ToV3(Color c) => new(c.r, c.g, c.b);
    private static Color FromV3(Vector3 v) => new(v.x, v.y, v.z);
}
