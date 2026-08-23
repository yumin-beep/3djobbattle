using Photon.Pun;
using UnityEngine;

/// 접속 화면, 직업 선택, HP/쿨다운, 머리 위 HP바, 매치 상태 표시 (IMGUI)
public class GameHUD : MonoBehaviour
{
    private PlayerHealth[] allPlayers = System.Array.Empty<PlayerHealth>();
    private float nextScan;

    private GUIStyle titleStyle, bigStyle, midStyle, smallStyle, descStyle;
    private bool stylesReady;

    private void Update()
    {
        if (Time.time < nextScan) return;
        allPlayers = FindObjectsByType<PlayerHealth>(FindObjectsSortMode.None);
        nextScan = Time.time + 0.5f;
    }

    private void OnGUI()
    {
        EnsureStyles();

        if (!PhotonNetwork.InRoom)
        {
            DrawConnectPanel();
            return;
        }

        DrawOverheadBars();
        DrawStateBanner();

        var pc = PlayerController.LocalPlayer;
        if (pc == null)
        {
            GUI.Label(new Rect(0, Screen.height * 0.45f, Screen.width, 40), "캐릭터 생성 중...", midStyle);
            return;
        }

        var pJob = pc.GetComponent<PlayerJob>();
        if (pJob.Job == JobType.None) DrawJobSelect(pJob);
        else DrawPlayerHUD(pc);

        DrawMasterControls();
    }

    private void EnsureStyles()
    {
        if (stylesReady) return;
        stylesReady = true;
        titleStyle = new GUIStyle(GUI.skin.label) { fontSize = 42, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
        bigStyle = new GUIStyle(GUI.skin.label) { fontSize = 30, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
        midStyle = new GUIStyle(GUI.skin.label) { fontSize = 18, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
        smallStyle = new GUIStyle(GUI.skin.label) { fontSize = 12, alignment = TextAnchor.MiddleCenter };
        descStyle = new GUIStyle(GUI.skin.label) { fontSize = 12, alignment = TextAnchor.UpperLeft, wordWrap = true };
        titleStyle.normal.textColor = bigStyle.normal.textColor = midStyle.normal.textColor = smallStyle.normal.textColor = descStyle.normal.textColor = Color.white;
    }

    // ---------- 접속 화면 ----------

    private void DrawConnectPanel()
    {
        float w = 440f, h = 280f;
        var rect = new Rect((Screen.width - w) / 2f, (Screen.height - h) / 2f, w, h);
        GUI.Box(rect, "");
        GUILayout.BeginArea(rect);
        GUILayout.Space(16);
        GUILayout.Label("현대 직업대전", titleStyle);
        GUILayout.Label("4인 멀티플레이 · 마지막 1인 생존", smallStyle);
        GUILayout.Space(20);

        string appId = PhotonNetwork.PhotonServerSettings.AppSettings.AppIdRealtime;
        if (string.IsNullOrEmpty(appId))
        {
            GUILayout.Label("Photon App ID가 설정되지 않았습니다!", midStyle);
            GUILayout.Label("메뉴 Window > Photon Unity Networking > PUN Wizard에서\ndashboard.photonengine.com의 App ID를 입력하세요.", smallStyle);
        }
        else
        {
            var launcher = NetworkLauncher.Instance;
            bool busy = launcher == null || launcher.Connecting || PhotonNetwork.IsConnected;
            GUI.enabled = !busy;
            if (GUILayout.Button("게임 접속", GUILayout.Height(52)) && launcher != null)
                launcher.Connect();
            GUI.enabled = true;

            GUILayout.Space(10);
            if (launcher != null && !string.IsNullOrEmpty(launcher.Status))
                GUILayout.Label(launcher.Status, midStyle);
            GUILayout.Label("자동으로 빈 방을 찾아 입장합니다 (인터넷만 있으면 어디서든 함께 플레이!)", smallStyle);
        }
        GUILayout.EndArea();
    }

    // ---------- 직업 선택 ----------

    private void DrawJobSelect(PlayerJob pJob)
    {
        float cardW = 200f, cardH = 190f, gap = 14f;
        int count = JobDatabase.Selectable.Length;
        float totalW = cardW * count + gap * (count - 1);
        float x0 = (Screen.width - totalW) / 2f;
        float y0 = Screen.height * 0.35f;

        GUI.Label(new Rect(0, y0 - 70, Screen.width, 50), "직업을 선택하세요", bigStyle);

        for (int i = 0; i < count; i++)
        {
            var type = JobDatabase.Selectable[i];
            var data = JobDatabase.Get(type);
            var rect = new Rect(x0 + i * (cardW + gap), y0, cardW, cardH);

            GUI.backgroundColor = data.color;
            GUI.Box(rect, "");
            GUI.backgroundColor = Color.white;

            GUI.Label(new Rect(rect.x, rect.y + 8, rect.width, 30), data.name, midStyle);
            GUI.Label(new Rect(rect.x, rect.y + 36, rect.width, 20), $"HP {data.maxHp} · 속도 {data.moveSpeed}", smallStyle);
            GUI.Label(new Rect(rect.x + 10, rect.y + 58, rect.width - 20, 90), data.desc, descStyle);

            if (GUI.Button(new Rect(rect.x + 10, rect.y + cardH - 38, rect.width - 20, 30), "선택"))
                pJob.SelectJob(type);
        }
    }

    // ---------- 플레이어 HUD ----------

    private void DrawPlayerHUD(PlayerController pc)
    {
        var health = pc.GetComponent<PlayerHealth>();
        var pJob = pc.GetComponent<PlayerJob>();
        var combat = pc.GetComponent<PlayerCombat>();
        var data = JobDatabase.Get(pJob.Job);

        // HP 바 (좌하단)
        float x = 20f, y = Screen.height - 90f, barW = 280f, barH = 26f;
        GUI.Label(new Rect(x, y - 26, barW, 24), pJob.DisplayName, midStyle);
        DrawBar(new Rect(x, y, barW, barH), (float)health.Hp / Mathf.Max(1, health.MaxHp),
            new Color(0.85f, 0.2f, 0.2f), $"{health.Hp} / {health.MaxHp}");

        // 상태 효과 표시
        float fx = x;
        if (health.ShieldRemaining > 0)
        {
            GUI.Label(new Rect(fx, y + barH + 4, 140, 20), $"[방패 {health.ShieldRemaining:F1}s]", smallStyle);
            fx += 140;
        }
        if (health.BuffRemaining > 0)
            GUI.Label(new Rect(fx, y + barH + 4, 140, 20), $"[상한가 {health.BuffRemaining:F1}s]", smallStyle);
        if (health.IsStunned)
            GUI.Label(new Rect(0, Screen.height * 0.4f, Screen.width, 40), "기절!", bigStyle);

        // 스킬 슬롯 (중앙 하단)
        string[] keys = { "좌클릭", "Q", "E" };
        float slotW = 120f, slotH = 58f, slotGap = 10f;
        float sx = (Screen.width - (slotW * 3 + slotGap * 2)) / 2f;
        float sy = Screen.height - slotH - 16f;

        for (int i = 0; i < 3; i++)
        {
            var rect = new Rect(sx + i * (slotW + slotGap), sy, slotW, slotH);
            GUI.Box(rect, "");
            GUI.Label(new Rect(rect.x, rect.y + 4, rect.width, 20), data.skillNames[i], smallStyle);
            float remain = combat.LocalReadyTime[i] - Time.time;
            if (remain > 0.05f)
            {
                GUI.color = new Color(1f, 1f, 1f, 0.35f);
                GUI.DrawTexture(rect, Texture2D.whiteTexture);
                GUI.color = Color.white;
                GUI.Label(new Rect(rect.x, rect.y + 26, rect.width, 26), $"{remain:F1}", midStyle);
            }
            else
            {
                GUI.Label(new Rect(rect.x, rect.y + 26, rect.width, 26), keys[i], midStyle);
            }
        }

        // 사망 시 리스폰 안내
        if (health.IsDead)
            GUI.Label(new Rect(0, Screen.height * 0.35f, Screen.width, 50),
                $"쓰러짐! {health.RespawnRemaining:F0}초 후 부활", bigStyle);

        // 로비에서 직업 다시 고르기
        var gm = GameManager.Instance;
        if (gm != null && gm.State == GameState.Lobby)
        {
            if (GUI.Button(new Rect(20, Screen.height - 140, 120, 30), "직업 변경"))
                pJob.ResetJob();
        }
    }

    // ---------- 상태 배너 ----------

    private void DrawStateBanner()
    {
        var gm = GameManager.Instance;
        if (gm == null) return;

        switch (gm.State)
        {
            case GameState.Lobby:
                GUI.Label(new Rect(0, 14, Screen.width, 30),
                    $"로비 · 연습 모드 (접속 {PhotonNetwork.CurrentRoom.PlayerCount}명) — 방장이 시작하면 5분 점령전!", midStyle);
                GUI.Label(new Rect(0, 42, Screen.width, 22),
                    "중앙 스팟에 '혼자' 3초간 서 있으면 점령 — 가장 오래 점령한 사람이 승리!", smallStyle);
                break;
            case GameState.Battle:
                double remain = gm.RemainingTime;
                var cp = CapturePoint.Instance;
                string owner = "없음";
                if (cp != null)
                {
                    var op = PlayerJob.FindByActor(cp.OwnerActor);
                    if (op != null) owner = op.DisplayName;
                }
                GUI.Label(new Rect(0, 14, Screen.width, 30),
                    $"남은 시간 {(int)(remain / 60)}:{(int)remain % 60:00} · 점령자: {owner}", midStyle);
                DrawCaptureProgress(cp);
                DrawScoreboard(cp);
                break;
            case GameState.GameOver:
                GUI.Label(new Rect(0, Screen.height * 0.2f, Screen.width, 60), $"{gm.Winner} 승리!", titleStyle);
                GUI.Label(new Rect(0, Screen.height * 0.2f + 60, Screen.width, 30), "잠시 후 로비로 돌아갑니다...", midStyle);
                break;
        }
    }

    private void DrawCaptureProgress(CapturePoint cp)
    {
        if (cp == null || cp.CaptureActor == -1) return;
        var capturing = PlayerJob.FindByActor(cp.CaptureActor);
        if (capturing == null) return;

        float w = 320f;
        var rect = new Rect((Screen.width - w) / 2f, 50, w, 22);
        Color color = JobDatabase.Get(capturing.Job).color;
        DrawBar(rect, cp.Progress / CapturePoint.CaptureTime, color,
            $"{capturing.DisplayName} 점령 중...");
    }

    private void DrawScoreboard(CapturePoint cp)
    {
        if (cp == null) return;

        var combatants = new System.Collections.Generic.List<PlayerJob>();
        foreach (var pj in GameManager.AllCombatants())
            if (pj.Job != JobType.None) combatants.Add(pj);
        combatants.Sort((a, b) => cp.GetHold(b.Actor).CompareTo(cp.GetHold(a.Actor)));

        float y = 50f;
        GUI.Box(new Rect(14, y - 6, 210, combatants.Count * 22 + 12), "");
        foreach (var pj in combatants)
        {
            var style = new GUIStyle(smallStyle) { alignment = TextAnchor.MiddleLeft };
            style.normal.textColor = JobDatabase.Get(pj.Job).color;
            GUI.Label(new Rect(24, y, 200, 20),
                $"{pj.DisplayName}  {cp.GetHold(pj.Actor):F0}초", style);
            y += 22f;
        }
    }

    // ---------- 방장 컨트롤 ----------

    private void DrawMasterControls()
    {
        var gm = GameManager.Instance;
        if (gm == null || !PhotonNetwork.IsMasterClient || gm.State != GameState.Lobby) return;

        if (gm.CanStartMatch(out string reason))
        {
            GUI.backgroundColor = new Color(0.3f, 0.9f, 0.4f);
            if (GUI.Button(new Rect(Screen.width - 180, 50, 160, 46), "게임 시작!"))
                gm.StartMatch();
            GUI.backgroundColor = Color.white;
        }
        else
        {
            GUI.Label(new Rect(Screen.width - 330, 50, 310, 46), reason, smallStyle);
        }

        // AI 봇 추가/제거 (연습용)
        int total = PhotonNetwork.CurrentRoom.PlayerCount + gm.BotCount;
        if (total < 4 && GUI.Button(new Rect(Screen.width - 180, 104, 160, 34), $"AI 추가 ({gm.BotCount})"))
            gm.AddBot();
        if (gm.BotCount > 0 && GUI.Button(new Rect(Screen.width - 180, 144, 160, 34), "AI 제거"))
            gm.RemoveBot();
    }

    // ---------- 머리 위 HP바 ----------

    private void DrawOverheadBars()
    {
        var cam = Camera.main;
        if (cam == null) return;

        foreach (var p in allPlayers)
        {
            if (p == null || p.IsDead) continue;
            var pJob = p.GetComponent<PlayerJob>();
            if (pJob.Job == JobType.None) continue;

            Vector3 screen = cam.WorldToScreenPoint(p.transform.position + Vector3.up * 2.8f);
            if (screen.z < 0) continue;

            float x = screen.x, y = Screen.height - screen.y;
            var data = JobDatabase.Get(pJob.Job);
            GUI.Label(new Rect(x - 60, y - 22, 120, 18), pJob.DisplayName, smallStyle);
            DrawBar(new Rect(x - 35, y, 70, 8), (float)p.Hp / Mathf.Max(1, p.MaxHp), data.color, "");
        }
    }

    private void DrawBar(Rect rect, float fill, Color color, string text)
    {
        GUI.color = new Color(0f, 0f, 0f, 0.6f);
        GUI.DrawTexture(rect, Texture2D.whiteTexture);
        GUI.color = color;
        GUI.DrawTexture(new Rect(rect.x, rect.y, rect.width * Mathf.Clamp01(fill), rect.height), Texture2D.whiteTexture);
        GUI.color = Color.white;
        if (!string.IsNullOrEmpty(text)) GUI.Label(rect, text, smallStyle);
    }
}
