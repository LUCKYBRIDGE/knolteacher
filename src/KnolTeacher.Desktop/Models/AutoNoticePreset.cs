using System;
using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class AutoNoticePreset
{
    public bool Enabled { get; set; } = false;
    public string MorningNotice { get; set; } = "외투와 실내화를 바르게 정리하고 아침 독서를 시작해요.";
    public string ClassNotice { get; set; } = "바른 자세로 선생님과 친구들의 발표에 귀 기울여요.";
    public string BreakNotice { get; set; } = "복도에서 뛰지 않고, 다음 시간 교과서와 필기도구를 준비해요.";
    public string LunchNotice { get; set; } = "비누로 손을 깨끗이 씻고 차례차례 급식실로 이동해요.";
    public string DismissalNotice { get; set; } = "내 자리 주변을 정리정돈하고 알림장을 확인해요.";
}

public class BoardSetItem
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Name { get; set; } = "기본 알림";
    public string Content { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.Now;
}

public class BoardSetStore
{
    public string ActiveSetId { get; set; } = string.Empty;
    public List<BoardSetItem> Sets { get; set; } = new();
}
