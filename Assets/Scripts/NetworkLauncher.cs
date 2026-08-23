using Photon.Pun;
using Photon.Realtime;
using UnityEngine;

/// Photon 접속 → 랜덤 방 입장(없으면 생성, 최대 4인) → 내 캐릭터 생성
public class NetworkLauncher : MonoBehaviourPunCallbacks
{
    public static NetworkLauncher Instance { get; private set; }

    public string Status { get; private set; } = "";
    public bool Connecting { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    public void Connect()
    {
        if (Connecting || PhotonNetwork.IsConnected) return;
        Connecting = true;
        Status = "Photon 서버 접속 중...";
        PhotonNetwork.NickName = "Player" + Random.Range(1000, 9999);
        PhotonNetwork.GameVersion = "1";
        PhotonNetwork.ConnectUsingSettings();
    }

    public override void OnConnectedToMaster()
    {
        Status = "방 찾는 중...";
        PhotonNetwork.JoinRandomRoom();
    }

    public override void OnJoinRandomFailed(short returnCode, string message)
    {
        Status = "방 만드는 중...";
        PhotonNetwork.CreateRoom(null, new RoomOptions { MaxPlayers = 4 });
    }

    public override void OnJoinedRoom()
    {
        Status = "";
        Connecting = false;
        Vector3 spawn = GameManager.GetSpawnPoint(PhotonNetwork.LocalPlayer.ActorNumber);
        PhotonNetwork.Instantiate("Player", spawn, Quaternion.identity);

        // 첫 입장자(방장)가 중앙 점령 스팟을 생성 (룸 오브젝트라 방장이 바뀌어도 유지됨)
        if (PhotonNetwork.IsMasterClient && CapturePoint.Instance == null)
            PhotonNetwork.InstantiateRoomObject("CapturePoint", Vector3.zero, Quaternion.identity);
    }

    public override void OnDisconnected(DisconnectCause cause)
    {
        Connecting = false;
        Status = $"연결 끊김: {cause}";
        CameraFollow.Target = null;
    }
}
