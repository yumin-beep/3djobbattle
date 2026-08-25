using UnityEngine;

/// 캐릭터 모델의 Animator 구동.
/// 이동 속도는 실제 위치 변화량으로 계산하므로 내 캐릭터·원격·AI 모두 동일하게 동작한다.
public class PlayerAnimator : MonoBehaviour
{
    private Animator animator;
    private Vector3 lastPos;
    private float smoothSpeed;

    private void Awake()
    {
        RefreshAnimator();
        lastPos = transform.position;
    }

    /// 직업 변경으로 비주얼이 바뀐 뒤 PlayerJob이 호출
    public void RefreshAnimator()
    {
        animator = GetComponentInChildren<Animator>(true);
        smoothSpeed = 0f;
    }

    private void Update()
    {
        Vector3 delta = transform.position - lastPos;
        delta.y = 0f;
        lastPos = transform.position;

        if (animator == null || !animator.gameObject.activeInHierarchy) return;

        float speed = delta.magnitude / Mathf.Max(Time.deltaTime, 0.0001f);
        smoothSpeed = Mathf.Lerp(smoothSpeed, speed, 12f * Time.deltaTime);
        animator.SetFloat("Speed", smoothSpeed);
    }

    public void PlayAttack()
    {
        if (animator != null && animator.gameObject.activeInHierarchy)
            animator.SetTrigger("Attack");
    }
}
