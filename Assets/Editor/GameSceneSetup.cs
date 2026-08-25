using System.Collections.Generic;
using Photon.Pun;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// 메뉴 한 번 클릭으로 직업대전 씬(맵, 플레이어 프리팹, 매니저, HUD)을 자동 구성 (PUN 2)
public static class GameSceneSetup
{
    private const string ResourcesDir = "Assets/Resources"; // PhotonNetwork.Instantiate용
    private const string MaterialDir = "Assets/Materials";
    private const string BakerCatFbx = "Assets/Art/Characters/char_baker_cat_rigged.fbx";

    [MenuItem("Tools/직업대전/씬 자동 설정")]
    public static void Setup()
    {
        EnsureFolder(ResourcesDir);
        EnsureFolder(MaterialDir);

        DisableTutorialPlayer();
        RemoveLegacyObjects();
        BuildArena();

        ConfigureCharacterModel(BakerCatFbx);
        ConfigureLighting();
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
        temp.AddComponent<BotBrain>();       // AI로 생성될 때만 활동
        temp.AddComponent<PlayerAnimator>(); // 모델 애니메이션 구동

        // 위치/회전 + 체력·상태이상 동기화
        pv.ObservedComponents = new List<Component> { ptv, health };
        pv.Synchronization = ViewSynchronization.UnreliableOnChange;

        // ----- 기본 비주얼: 직업 색 캡슐 (모델 없는 직업용) -----
        var capsuleRoot = new GameObject("Visual_Capsule");
        capsuleRoot.transform.SetParent(temp.transform, false);

        var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.name = "Body";
        Object.DestroyImmediate(body.GetComponent<Collider>());
        body.transform.SetParent(capsuleRoot.transform);
        body.transform.localPosition = new Vector3(0f, 1f, 0f);

        var hat = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hat.name = "Hat";
        Object.DestroyImmediate(hat.GetComponent<Collider>());
        hat.transform.SetParent(capsuleRoot.transform);
        hat.transform.localPosition = new Vector3(0f, 2.2f, 0f);
        hat.transform.localScale = new Vector3(0.7f, 0.25f, 0.7f);

        var nose = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nose.name = "Nose";
        Object.DestroyImmediate(nose.GetComponent<Collider>());
        nose.transform.SetParent(capsuleRoot.transform);
        nose.transform.localPosition = new Vector3(0f, 1.5f, 0.5f);
        nose.transform.localScale = new Vector3(0.22f, 0.22f, 0.45f);

        // ----- 빵집사장 고양이 모델 (있을 때만) -----
        var catModel = AssetDatabase.LoadAssetAtPath<GameObject>(BakerCatFbx);
        if (catModel != null)
        {
            var cat = (GameObject)PrefabUtility.InstantiatePrefab(catModel);
            cat.name = "Visual_BakerCat";
            cat.transform.SetParent(temp.transform, false);
            cat.transform.localPosition = Vector3.zero;
            cat.transform.localRotation = Quaternion.identity;

            var animator = cat.GetComponent<Animator>();
            if (animator == null) animator = cat.AddComponent<Animator>();
            animator.runtimeAnimatorController = BuildCharacterAnimator(BakerCatFbx, "BakerCat");
            animator.applyRootMotion = false;

            // 원본에서 모자 돔(Hat_Puff)에 머티리얼 할당이 누락됨 — 빈 슬롯을 Warm_White로 보정
            var warmWhite = AssetDatabase.LoadAssetAtPath<Material>(
                "Assets/Art/Characters/Materials/BC3_Mat_Warm_White.mat");
            if (warmWhite != null)
            {
                foreach (var r in cat.GetComponentsInChildren<Renderer>(true))
                {
                    var mats = r.sharedMaterials;
                    bool changed = false;
                    for (int i = 0; i < mats.Length; i++)
                    {
                        bool empty = mats[i] == null || mats[i].name.Contains("No Name") || mats[i].name.Contains("Default");
                        if (empty || r.gameObject.name.Contains("Hat_Puff"))
                        {
                            mats[i] = warmWhite;
                            changed = true;
                        }
                    }
                    if (changed) r.sharedMaterials = mats;
                }
            }

            cat.SetActive(false); // PlayerJob이 직업에 따라 켬
        }
        else
        {
            Debug.LogWarning($"고양이 모델을 찾지 못했습니다: {BakerCatFbx} — 캡슐 비주얼만 사용합니다.");
        }

        // private [SerializeField] projectilePrefab 할당
        var so = new SerializedObject(combat);
        so.FindProperty("projectilePrefab").objectReferenceValue = projectilePrefab;
        so.ApplyModifiedPropertiesWithoutUndo();

        PrefabUtility.SaveAsPrefabAsset(temp, $"{ResourcesDir}/Player.prefab");
        Object.DestroyImmediate(temp);

        // 같은 배치에서 새로 만든 에셋(컨트롤러 등)을 참조하므로, 강제 리임포트로
        // 프리팹 임포트 캐시의 참조가 확실히 갱신되게 한다.
        AssetDatabase.SaveAssets();
        AssetDatabase.ImportAsset($"{ResourcesDir}/Player.prefab", ImportAssetOptions.ForceUpdate);
    }

    /// FBX 임포트 설정: Generic 릭, Idle/Run 루프, 클립 이름 정규화,
    /// 내장 텍스처·머티리얼 추출 + 무광 처리
    private static void ConfigureCharacterModel(string fbxPath)
    {
        var importer = AssetImporter.GetAtPath(fbxPath) as ModelImporter;
        if (importer == null) return; // 모델이 아직 없음

        importer.animationType = ModelImporterAnimationType.Generic;
        importer.importCameras = false;
        importer.importLights = false;

        var clips = importer.defaultClipAnimations;
        foreach (var clip in clips)
        {
            if (clip.name.Contains("Idle")) clip.name = "Idle";
            else if (clip.name.Contains("Run")) clip.name = "Run";
            else if (clip.name.Contains("Attack")) clip.name = "Attack";
            clip.loopTime = clip.name is "Idle" or "Run";
        }
        if (clips.Length > 0) importer.clipAnimations = clips;
        importer.SaveAndReimport();

        // FBX에 내장된 텍스처 추출 (바게트 칼집 등)
        string texDir = "Assets/Art/Characters/Textures";
        EnsureFolder(texDir);
        importer.ExtractTextures(texDir);

        // 머티리얼을 편집 가능한 에셋으로 추출
        string matDir = "Assets/Art/Characters/Materials";
        EnsureFolder(matDir);
        bool extractedAny = false;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(fbxPath))
        {
            if (asset is not Material embedded) continue;
            string dest = $"{matDir}/{embedded.name}.mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(dest) != null) continue;
            string error = AssetDatabase.ExtractAsset(embedded, dest);
            if (string.IsNullOrEmpty(error)) extractedAny = true;
        }
        if (extractedAny)
        {
            AssetDatabase.WriteImportSettingsIfDirty(fbxPath);
            AssetDatabase.ImportAsset(fbxPath, ImportAssetOptions.ForceUpdate);
        }

        // 전부 무광 처리 (플랫 스타일 — 하늘 반사로 회청색 되는 것 방지)
        var materials = new List<Material>();
        foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { matDir }))
        {
            var mat = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
            if (mat == null) continue;
            materials.Add(mat);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", 0f);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(mat);
        }

        // FBX가 텍스처-머티리얼 연결 정보를 누락한 경우, 이름 매칭으로 직접 연결
        foreach (var texGuid in AssetDatabase.FindAssets("t:Texture2D", new[] { texDir }))
        {
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(AssetDatabase.GUIDToAssetPath(texGuid));
            if (tex == null) continue;
            string texName = tex.name.ToLowerInvariant();
            foreach (var mat in materials)
            {
                string matName = mat.name.ToLowerInvariant();
                bool matches = matName.Contains("baguette") && texName.Contains("baguette");
                if (!matches || mat.GetTexture("_BaseMap") != null) continue;
                mat.SetTexture("_BaseMap", tex);
                mat.SetColor("_BaseColor", Color.white); // 텍스처 색이 그대로 나오게
                EditorUtility.SetDirty(mat);
            }
        }
        AssetDatabase.SaveAssets();
    }

    /// 플랫 카툰 스타일용 조명: 파란 하늘빛 대신 중립 앰비언트 (흰 모자가 회청색으로 보이는 문제 해결)
    private static void ConfigureLighting()
    {
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.76f, 0.75f, 0.72f);

        var light = Object.FindFirstObjectByType<Light>();
        if (light != null && light.type == LightType.Directional)
        {
            light.color = new Color(1f, 0.98f, 0.94f);
            light.intensity = 1.1f;
            light.shadows = LightShadows.Soft;
        }
    }

    /// FBX의 Idle/Run/Attack 클립으로 Animator Controller 생성 (Speed float, Attack trigger)
    private static RuntimeAnimatorController BuildCharacterAnimator(string fbxPath, string charName)
    {
        string ctrlPath = $"Assets/Art/Characters/{charName}Animator.controller";
        // 기존 에셋을 삭제하면 GUID·임포트 캐시가 끊겨 이미 저장된 프리팹의 컨트롤러 참조가
        // NULL이 된다(재실행 때마다 애니메이션이 죽는 원인). 있으면 내용만 비우고 재사용한다.
        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(ctrlPath);
        if (ctrl == null)
        {
            ctrl = AnimatorController.CreateAnimatorControllerAtPath(ctrlPath);
        }
        else
        {
            var oldSm = ctrl.layers[0].stateMachine;
            foreach (var child in oldSm.states)
                oldSm.RemoveState(child.state);
            foreach (var t in oldSm.anyStateTransitions)
                oldSm.RemoveAnyStateTransition(t);
            ctrl.parameters = new AnimatorControllerParameter[0];
        }
        ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);
        ctrl.AddParameter("Attack", AnimatorControllerParameterType.Trigger);

        AnimationClip idle = null, run = null, attack = null;
        foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(fbxPath))
        {
            if (asset is not AnimationClip clip || clip.name.StartsWith("__preview")) continue;
            if (clip.name.EndsWith("Idle")) idle = clip;
            else if (clip.name.EndsWith("Run")) run = clip;
            else if (clip.name.EndsWith("Attack")) attack = clip;
        }

        var sm = ctrl.layers[0].stateMachine;
        var sIdle = sm.AddState("Idle");
        sIdle.motion = idle;
        var sRun = sm.AddState("Run");
        sRun.motion = run;
        sm.defaultState = sIdle;

        var toRun = sIdle.AddTransition(sRun);
        toRun.AddCondition(AnimatorConditionMode.Greater, 0.5f, "Speed");
        toRun.hasExitTime = false;
        toRun.duration = 0.1f;

        var toIdle = sRun.AddTransition(sIdle);
        toIdle.AddCondition(AnimatorConditionMode.Less, 0.5f, "Speed");
        toIdle.hasExitTime = false;
        toIdle.duration = 0.1f;

        if (attack != null)
        {
            var sAttack = sm.AddState("Attack");
            sAttack.motion = attack;

            var toAttack = sm.AddAnyStateTransition(sAttack);
            toAttack.AddCondition(AnimatorConditionMode.If, 0f, "Attack");
            toAttack.hasExitTime = false;
            toAttack.duration = 0.05f;
            toAttack.canTransitionToSelf = false;

            var backToIdle = sAttack.AddTransition(sIdle);
            backToIdle.hasExitTime = true;
            backToIdle.exitTime = 0.95f;
            backToIdle.duration = 0.1f;
        }

        return ctrl;
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
