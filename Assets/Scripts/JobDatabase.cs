using UnityEngine;

public enum JobType : byte
{
    None = 0,
    Baker = 1,        // 빵집사장
    Police = 2,       // 경찰
    Trader = 3,       // 트레이더
    Firefighter = 4,  // 소방관
}

public struct JobData
{
    public string name;
    public Color color;
    public int maxHp;
    public float moveSpeed;
    public float[] cooldowns;    // [기본공격, 스킬1(Q), 스킬2(E)]
    public string[] skillNames;
    public string desc;
}

public static class JobDatabase
{
    public static readonly JobType[] Selectable =
    {
        JobType.Baker, JobType.Police, JobType.Trader, JobType.Firefighter,
    };

    private static readonly JobData None = new()
    {
        name = "미선택",
        color = new Color(0.6f, 0.6f, 0.6f),
        maxHp = 200,
        moveSpeed = 5.5f,
        cooldowns = new[] { 1f, 1f, 1f },
        skillNames = new[] { "-", "-", "-" },
        desc = "직업을 선택하세요",
    };

    private static readonly JobData Baker = new()
    {
        name = "빵집사장",
        color = new Color(0.95f, 0.8f, 0.5f),
        maxHp = 220,
        moveSpeed = 5.5f,
        cooldowns = new[] { 0.6f, 8f, 12f },
        skillNames = new[] { "바게트 스윙", "밀가루 폭탄", "갓 구운 빵" },
        desc = "근접 강타와 자가 회복을 갖춘 브루저.\nQ: 밀가루 폭탄 (범위 피해 + 슬로우)\nE: 갓 구운 빵 (체력 60 회복)",
    };

    private static readonly JobData Police = new()
    {
        name = "경찰",
        color = new Color(0.25f, 0.45f, 1f),
        maxHp = 200,
        moveSpeed = 6f,
        cooldowns = new[] { 0.45f, 9f, 10f },
        skillNames = new[] { "권총 사격", "테이저건", "진압 방패" },
        desc = "원거리 견제와 제압의 밸런스형.\nQ: 테이저건 (명중 시 1.5초 스턴)\nE: 진압 방패 (3초간 받는 피해 60% 감소)",
    };

    private static readonly JobData Trader = new()
    {
        name = "트레이더",
        color = new Color(1f, 0.8f, 0.2f),
        maxHp = 170,
        moveSpeed = 6.5f,
        cooldowns = new[] { 0.35f, 10f, 12f },
        skillNames = new[] { "동전 던지기", "몰빵", "상한가" },
        desc = "빠르지만 체력이 낮은 하이리스크 딜러.\nQ: 몰빵 (내 HP 20 소모, 강력한 황금 동전)\nE: 상한가 (4초간 공격력 50% 증가)",
    };

    private static readonly JobData Firefighter = new()
    {
        name = "소방관",
        color = new Color(0.9f, 0.25f, 0.2f),
        maxHp = 260,
        moveSpeed = 5f,
        cooldowns = new[] { 0.8f, 9f, 8f },
        skillNames = new[] { "소방도끼", "물대포", "긴급출동" },
        desc = "높은 체력의 탱커.\nQ: 물대포 (전방 범위 피해 + 넉백)\nE: 긴급출동 (전방 돌진, 부딪힌 적 피해)",
    };

    public static JobData Get(JobType type) => type switch
    {
        JobType.Baker => Baker,
        JobType.Police => Police,
        JobType.Trader => Trader,
        JobType.Firefighter => Firefighter,
        _ => None,
    };
}
