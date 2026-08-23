using Photon.Pun;
using UnityEngine;
using UnityEngine.InputSystem;

/// 내 캐릭터의 이동/조준/점프/넉백/돌진. WASD 이동 + 마우스 조준 (쿼터뷰)
[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviourPun
{
    public static PlayerController LocalPlayer { get; private set; }

    [SerializeField] private float jumpForce = 7f;
    [SerializeField] private float gravity = -25f;

    private CharacterController controller;
    private PlayerHealth health;
    private PlayerJob job;
    private BotBrain brain;
    private float verticalVelocity;
    private Vector3 knockback;
    private float dashTimeLeft;
    private Vector3 dashDir;

    public Vector3 AimDirection { get; private set; } = Vector3.forward;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
        health = GetComponent<PlayerHealth>();
        job = GetComponent<PlayerJob>();
        brain = GetComponent<BotBrain>();
    }

    private void Start()
    {
        if (!photonView.IsMine || job.IsBot) return;
        LocalPlayer = this;
        CameraFollow.Target = transform;
        TeleportLocal(GameManager.GetSpawnPoint(PhotonNetwork.LocalPlayer.ActorNumber));
    }

    private void Update()
    {
        if (!photonView.IsMine || health.IsDead) return;

        // 조준: 사람은 마우스, AI는 BotBrain
        if (job.IsBot)
        {
            if (brain != null && brain.AimDir.sqrMagnitude > 0.001f) AimDirection = brain.AimDir.normalized;
        }
        else
        {
            UpdateAim();
        }

        float dt = Time.deltaTime;
        Vector3 motion = Vector3.zero;

        if (dashTimeLeft > 0f)
        {
            dashTimeLeft -= dt;
            motion += dashDir * 34f;
        }
        else if (!health.IsStunned)
        {
            Vector2 input = Vector2.zero;
            if (job.IsBot)
            {
                if (brain != null) input = brain.MoveInput;
            }
            else
            {
                var kb = Keyboard.current;
                if (kb != null)
                {
                    if (kb.wKey.isPressed || kb.upArrowKey.isPressed) input.y += 1f;
                    if (kb.sKey.isPressed || kb.downArrowKey.isPressed) input.y -= 1f;
                    if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) input.x += 1f;
                    if (kb.aKey.isPressed || kb.leftArrowKey.isPressed) input.x -= 1f;
                    if (kb.spaceKey.wasPressedThisFrame && controller.isGrounded) verticalVelocity = jumpForce;
                }
            }

            Vector3 move = new(input.x, 0f, input.y);
            if (move.sqrMagnitude > 1f) move.Normalize();
            float speed = JobDatabase.Get(job.Job).moveSpeed * health.CurrentSpeedMult;
            motion += move * speed;
        }

        if (controller.isGrounded && verticalVelocity < 0f) verticalVelocity = -2f;
        verticalVelocity += gravity * dt;
        motion.y = verticalVelocity;

        motion += knockback;
        knockback = Vector3.MoveTowards(knockback, Vector3.zero, 20f * dt);

        controller.Move(motion * dt);

        // 조준 방향으로 회전
        Vector3 face = AimDirection;
        face.y = 0f;
        if (face.sqrMagnitude > 0.001f)
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(face), 15f * dt);
    }

    private void UpdateAim()
    {
        var cam = Camera.main;
        var mouse = Mouse.current;
        if (cam == null || mouse == null) return;

        Ray ray = cam.ScreenPointToRay(mouse.position.ReadValue());
        Plane plane = new(Vector3.up, new Vector3(0f, transform.position.y, 0f));
        if (!plane.Raycast(ray, out float dist)) return;

        Vector3 dir = ray.GetPoint(dist) - transform.position;
        dir.y = 0f;
        if (dir.sqrMagnitude > 0.04f) AimDirection = dir.normalized;
    }

    public void StartDash(Vector3 dir)
    {
        dashDir = dir;
        dashTimeLeft = 0.3f;
    }

    public void TeleportLocal(Vector3 pos)
    {
        if (!photonView.IsMine) return;
        controller.enabled = false;
        transform.position = pos;
        controller.enabled = true;
        verticalVelocity = 0f;
        knockback = Vector3.zero;
        dashTimeLeft = 0f;
    }

    /// 공격자가 피해자를 제어하는 클라이언트로 넉백 전달 (AI는 방장이 제어)
    public void SendKnockback(Vector3 impulse)
    {
        var controllerPlayer = photonView.Owner ?? PhotonNetwork.MasterClient;
        if (controllerPlayer == null) return;
        photonView.RPC(nameof(RpcKnockback), controllerPlayer, impulse);
    }

    [PunRPC]
    private void RpcKnockback(Vector3 impulse)
    {
        if (photonView.IsMine) knockback += impulse;
    }

    private void OnDestroy()
    {
        if (LocalPlayer == this) LocalPlayer = null;
    }
}
