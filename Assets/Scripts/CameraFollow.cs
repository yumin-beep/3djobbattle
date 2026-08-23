using UnityEngine;

/// 내 캐릭터를 쿼터뷰로 따라다니는 카메라
public class CameraFollow : MonoBehaviour
{
    public static Transform Target;

    [SerializeField] private Vector3 offset = new(0f, 13f, -9f);
    private Vector3 velocity;

    private void LateUpdate()
    {
        if (Target == null) return;

        Vector3 want = Target.position + offset;
        transform.position = Vector3.SmoothDamp(transform.position, want, ref velocity, 0.12f);
        transform.rotation = Quaternion.LookRotation(Target.position + Vector3.up - transform.position);
    }
}
