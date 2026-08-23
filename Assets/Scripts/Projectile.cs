using System.Collections.Generic;
using UnityEngine;

/// 투사체. 쏜 사람의 클라이언트에서만 판정하고,
/// 다른 클라이언트의 인스턴스는 같은 경로를 그리는 비주얼 전용.
public class Projectile : MonoBehaviour
{
    private static readonly Dictionary<long, Projectile> Live = new();

    private long key;
    private Vector3 dir;
    private float speed;
    private float life;
    private Color color;

    // 쏜 사람 클라이언트 전용
    private bool simulating;
    private PlayerCombat shooter;
    private int damage;
    private float stun;
    private float slowFactor = 1f;
    private float slowDur;
    private float aoeRadius;

    public void InitVisual(long key, Vector3 dir, float speed, float life, float scale, Color color)
    {
        this.key = key;
        this.dir = dir.normalized;
        this.speed = speed;
        this.life = life;
        this.color = color;
        transform.localScale = Vector3.one * scale;
        var r = GetComponent<Renderer>();
        if (r != null) r.material.SetColor("_BaseColor", color);
        Live[key] = this;
    }

    public void InitSim(PlayerCombat shooter, int damage, float stun, float slowFactor, float slowDur, float aoeRadius)
    {
        simulating = true;
        this.shooter = shooter;
        this.damage = damage;
        this.stun = stun;
        this.slowFactor = slowFactor;
        this.slowDur = slowDur;
        this.aoeRadius = aoeRadius;
    }

    private void Update()
    {
        float step = speed * Time.deltaTime;

        if (simulating && CheckHit(step)) return;

        transform.position += dir * step;
        life -= Time.deltaTime;
        if (life <= 0f) Remove();
    }

    private bool CheckHit(float step)
    {
        var hits = Physics.SphereCastAll(transform.position, 0.3f, dir, step + 0.05f);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));

        foreach (var hit in hits)
        {
            if (hit.collider.isTrigger) continue;

            var target = hit.collider.GetComponentInParent<PlayerHealth>();
            if (target != null)
            {
                if (target.gameObject == shooter.gameObject || target.IsDead) continue;
            }

            Vector3 hitPos = hit.distance > 0f ? hit.point : transform.position;

            if (aoeRadius > 0f) Explode(hitPos);
            else if (target != null) ApplyTo(target);
            // 환경 명중 + 비범위 투사체는 그냥 소멸

            shooter.BroadcastProjectileHit(key, hitPos, aoeRadius > 0f ? aoeRadius : 0.7f, color);
            Remove();
            return true;
        }
        return false;
    }

    private void ApplyTo(PlayerHealth target)
    {
        target.SendHit(damage, stun, slowFactor, slowDur);
    }

    private void Explode(Vector3 center)
    {
        var applied = new HashSet<PlayerHealth>();
        foreach (var col in Physics.OverlapSphere(center, aoeRadius))
        {
            var target = col.GetComponentInParent<PlayerHealth>();
            if (target == null || applied.Contains(target)) continue;
            if (target.gameObject == shooter.gameObject || target.IsDead) continue;
            applied.Add(target);
            ApplyTo(target);
        }
    }

    private void Remove()
    {
        Live.Remove(key);
        Destroy(gameObject);
    }

    public static void DestroyVisual(long key)
    {
        if (Live.TryGetValue(key, out var p)) p.Remove();
    }
}
