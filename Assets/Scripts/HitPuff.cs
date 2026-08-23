using UnityEngine;

/// 타격/폭발/스킬 시전을 표현하는 간단한 이펙트 (커지다가 사라지는 도형)
public class HitPuff : MonoBehaviour
{
    private float life;
    private float duration;
    private Vector3 startScale;
    private Vector3 endScale;

    public static void Create(Vector3 pos, float radius, Color color, float duration = 0.25f)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        Setup(go, pos, Quaternion.identity, Vector3.one * radius * 0.4f, Vector3.one * radius * 2f, color, duration);
    }

    public static void CreateBeam(Vector3 pos, Vector3 dir, float length, Color color, float duration = 0.25f)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        Vector3 center = pos + dir.normalized * (length * 0.5f);
        var scale = new Vector3(1.4f, 1.4f, length);
        Setup(go, center, Quaternion.LookRotation(dir), scale * 0.6f, scale, color, duration);
    }

    private static void Setup(GameObject go, Vector3 pos, Quaternion rot, Vector3 from, Vector3 to, Color color, float duration)
    {
        var collider = go.GetComponent<Collider>();
        if (collider != null) Destroy(collider);
        go.transform.SetPositionAndRotation(pos, rot);
        go.transform.localScale = from;
        go.GetComponent<Renderer>().material.SetColor("_BaseColor", color);

        var puff = go.AddComponent<HitPuff>();
        puff.duration = duration;
        puff.startScale = from;
        puff.endScale = to;
    }

    private void Update()
    {
        life += Time.deltaTime;
        if (life >= duration)
        {
            Destroy(gameObject);
            return;
        }
        transform.localScale = Vector3.Lerp(startScale, endScale, life / duration);
    }
}
