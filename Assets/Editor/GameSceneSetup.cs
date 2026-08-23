using System.Collections.Generic;
using Photon.Pun;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// 메뉴 한 번 클릭으로 직업대전 씬(맵, 플레이어 프리팹, 매니저, HUD)을 자동 구성 (PUN 2)
public static class GameSceneSetup
{
    private const string ResourcesDir = "Assets/Resources"; // PhotonNetwork.Instantiate용
    private const string MaterialDir = "Assets/Materials";

    [MenuItem("Tools/직업대전/씬 자동 설정")]
    public static void Setup()
    {
        EnsureFolder(ResourcesDir);
        EnsureFolder(MaterialDir);

        DisableTutorialPlayer();
        RemoveLegacyObjects();
        BuildArena();

        var projectilePrefab = BuildProjectilePrefab();
        BuildPlayerPrefab(projectilePrefab);
        BuildCapturePointPrefab();
        BuildManagers();
        SetupCamera();

        var scene = SceneManager.GetActiveScene();
        if (!string.IsNullOrEmpty(scene.path))
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scene.path, true) };

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveOpenScenes();

        Debug.Log("✅ 직업대전 씬 설정 완료! PUN Wizard에 App ID를 넣었는지 확인하고 Play를 누르세요.");
    }

    private static void DisableTutorialPlayer()
    {
        foreach (var pm in Object.FindObjectsByType<PlayerMove>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            pm.gameObject.SetActive(false);
            Debug.Log($"기존 튜토리얼 플레이어 '{pm.gameObject.name}' 비활성화");
        }
    }

    private static void RemoveLegacyObjects()
    {
        // 이전 Netcode 세팅에서 만들어졌을 수 있는 오브젝트 제거
        var legacy = GameObject.Find("NetworkManager");
        if (legacy != null) Object.DestroyImmediate(legacy);
    }

    private static void BuildArena()
    {
        var old = GameObject.Find("Arena");
        if (old != null) Object.DestroyImmediate(old);

        var root = new GameObject("Arena");

        var groundMat = GetMaterial("Ground", new Color(0.45f, 0.5f, 0.42f));
        var wallMat = GetMaterial("Wall", new Color(0.35f, 0.35f, 0.4f));
        var obstacleMat = GetMaterial("Obstacle", new Color(0.55f, 0.42f, 0.3f));

        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.SetParent(root.transform);
        ground.transform.localScale = new Vector3(4f, 1f, 4f); // 40x40
        ground.GetComponent<Renderer>().sharedMaterial = groundMat;

        // 외벽
        CreateBox(root, "Wall_N", new Vector3(0, 1.5f, 20.5f), new Vector3(42f, 3f, 1f), wallMat);
        CreateBox(root, "Wall_S", new Vector3(0, 1.5f, -20.5f), new Vector3(42f, 3f, 1f), wallMat);
        CreateBox(root, "Wall_E", new Vector3(20.5f, 1.5f, 0), new Vector3(1f, 3f, 42f), wallMat);
        CreateBox(root, "Wall_W", new Vector3(-20.5f, 1.5f, 0), new Vector3(1f, 3f, 42f), wallMat);

        // 엄폐물 (중앙은 점령 스팟 자리라 비워둠)
        CreateBox(root, "Obstacle_1", new Vector3(7f, 1f, 7f), new Vector3(3f, 2f, 3f), obstacleMat);
        CreateBox(root, "Obstacle_2", new Vector3(-7f, 1f, -7f), new Vector3(3f, 2f, 3f), obstacleMat);
        CreateBox(root, "Obstacle_3", new Vector3(-8f, 1f, 8f), new Vector3(2f, 2f, 5f), obstacleMat);
        CreateBox(root, "Obstacle_4", new Vector3(8f, 1f, -8f), new Vector3(5f, 2f, 2f), obstacleMat);
    }

    private static void CreateBox(GameObject parent, string name, Vector3 pos, Vector3 scale, Material mat)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent.transform);
        go.transform.position = pos;
        go.transform.localScale = scale;
        go.GetComponent<Renderer>().sharedMaterial = mat;
    }

    private static GameObject BuildProjectilePrefab()
    {
        var temp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        temp.name = "Projectile";
        Object.DestroyImmediate(temp.GetComponent<Collider>());
        temp.transform.localScale = Vector3.one * 0.3f;
        temp.AddComponent<Projectile>();

        var prefab = PrefabUtility.SaveAsPrefabAsset(temp, $"{ResourcesDir}/Projectile.prefab");
        Object.DestroyImmediate(temp);
        return prefab;
    }

    private static void BuildPlayerPrefab(GameObject projectilePrefab)
    {
        var temp = new GameObject("Player");

        var cc = temp.AddComponent<CharacterController>();
        cc.center = new Vector3(0f, 1f, 0f);
        cc.height = 2f;
        cc.radius = 0.5f;

        var pv = temp.AddComponent<PhotonView>();
        var ptv = temp.AddComponent<PhotonTransformView>();
        var health = temp.AddComponent<PlayerHealth>();
        temp.AddComponent<PlayerJob>();
        temp.AddComponent<PlayerController>();
        var combat = temp.AddComponent<PlayerCombat>();
        temp.AddComponent<BotBrain>(); // AI로 생성될 때만 활동

        // 위치/회전 + 체력·상태이상 동기화
        pv.ObservedComponents = new List<Component> { ptv, health };
        pv.Synchronization = ViewSynchronization.UnreliableOnChange;

        // 몸통
        var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.name = "Body";
        Object.DestroyImmediate(body.GetComponent<Collider>());
        body.transform.SetParent(temp.transform);
        body.transform.localPosition = new Vector3(0f, 1f, 0f);

        // 모자 (직업 색으로 물듦)
        var hat = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hat.name = "Hat";
        Object.DestroyImmediate(hat.GetComponent<Collider>());
        hat.transform.SetParent(temp.transform);
        hat.transform.localPosition = new Vector3(0f, 2.2f, 0f);
        hat.transform.localScale = new Vector3(0.7f, 0.25f, 0.7f);

        // 바라보는 방향 표시용 코
        var nose = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nose.name = "Nose";
        Object.DestroyImmediate(nose.GetComponent<Collider>());
        nose.transform.SetParent(temp.transform);
        nose.transform.localPosition = new Vector3(0f, 1.5f, 0.5f);
        nose.transform.localScale = new Vector3(0.22f, 0.22f, 0.45f);

        // private [SerializeField] projectilePrefab 할당
        var so = new SerializedObject(combat);
        so.FindProperty("projectilePrefab").objectReferenceValue = projectilePrefab;
        so.ApplyModifiedPropertiesWithoutUndo();

        PrefabUtility.SaveAsPrefabAsset(temp, $"{ResourcesDir}/Player.prefab");
        Object.DestroyImmediate(temp);
    }

    private static void BuildCapturePointPrefab()
    {
        var temp = new GameObject("CapturePoint");

        var pv = temp.AddComponent<PhotonView>();
        var cp = temp.AddComponent<CapturePoint>();
        pv.ObservedComponents = new List<Component> { cp };
        pv.Synchronization = ViewSynchronization.UnreliableOnChange;

        // 점령 패드 (반지름 3짜리 납작한 원판)
        var pad = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        pad.name = "Pad";
        Object.DestroyImmediate(pad.GetComponent<Collider>());
        pad.transform.SetParent(temp.transform);
        pad.transform.localPosition = new Vector3(0f, 0.05f, 0f);
        pad.transform.localScale = new Vector3(CapturePoint.Radius * 2f, 0.05f, CapturePoint.Radius * 2f);

        PrefabUtility.SaveAsPrefabAsset(temp, $"{ResourcesDir}/CapturePoint.prefab");
        Object.DestroyImmediate(temp);
    }

    private static void BuildManagers()
    {
        var gm = GameObject.Find("GameManager");
        if (gm == null) gm = new GameObject("GameManager");
        if (gm.GetComponent<GameManager>() == null) gm.AddComponent<GameManager>();

        var game = GameObject.Find("Game");
        if (game == null) game = new GameObject("Game");
        if (game.GetComponent<NetworkLauncher>() == null) game.AddComponent<NetworkLauncher>();
        if (game.GetComponent<GameHUD>() == null) game.AddComponent<GameHUD>();

        // 이전 세팅의 GameHUD 단독 오브젝트 정리
        var oldHud = GameObject.Find("GameHUD");
        if (oldHud != null) Object.DestroyImmediate(oldHud);
    }

    private static void SetupCamera()
    {
        var cam = Camera.main;
        if (cam == null) return;
        if (cam.GetComponent<CameraFollow>() == null) cam.gameObject.AddComponent<CameraFollow>();
        cam.transform.position = new Vector3(0f, 13f, -9f);
        cam.transform.rotation = Quaternion.Euler(52f, 0f, 0f);
    }

    private static Material GetMaterial(string name, Color color)
    {
        string path = $"{MaterialDir}/{name}.mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            mat = new Material(shader);
            AssetDatabase.CreateAsset(mat, path);
        }
        mat.SetColor("_BaseColor", color);
        EditorUtility.SetDirty(mat);
        return mat;
    }

    private static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        int idx = path.LastIndexOf('/');
        AssetDatabase.CreateFolder(path[..idx], path[(idx + 1)..]);
    }
}
