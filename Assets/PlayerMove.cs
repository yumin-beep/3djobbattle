using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(CharacterController))]
public class PlayerMove : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float jumpForce = 6f;
    [SerializeField] private float gravity = -20f;

    private CharacterController controller;
    private Vector2 moveInput;
    private float verticalVelocity;

    private void Awake()
    {
        controller = GetComponent<CharacterController>();
    }

    private void Update()
    {
        Move();
        ApplyGravity();
    }

    private void Move()
    {
        Vector3 move = transform.right * moveInput.x + transform.forward * moveInput.y;
        move.y = 0f;

        if (move.sqrMagnitude > 0.01f)
        {
            move.Normalize();
            controller.Move(move * moveSpeed * Time.deltaTime);
        }
    }

    private void ApplyGravity()
    {
        if (controller.isGrounded && verticalVelocity < 0f)
        {
            verticalVelocity = -2f;
        }

        verticalVelocity += gravity * Time.deltaTime;
        controller.Move(new Vector3(0f, verticalVelocity, 0f) * Time.deltaTime);
    }

    public void OnMove(InputValue value)
    {
        moveInput = value.Get<Vector2>();
    }

    public void OnJump(InputValue value)
    {
        if (!controller.isGrounded)
        {
            return;
        }

        float jumpPressed = value.Get<float>();

        if (jumpPressed > 0f)
        {
            verticalVelocity = jumpForce;
        }
    }
}
