using System;
using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class SchoolSearchResultItem
{
    public string SchoolCode { get; set; } = string.Empty;
    public string OfficeCode { get; set; } = string.Empty;
    public string OfficeName { get; set; } = string.Empty;
    public string SchoolName { get; set; } = string.Empty;
    public string SchoolType { get; set; } = string.Empty; // 초등학교, 중학교, 고등학교, 특수학교 등
    public string LocationName { get; set; } = string.Empty;
    public string JurisdictionName { get; set; } = string.Empty;
    public string FondType { get; set; } = string.Empty; // 공립, 사립, 국립
    public string RoadAddress { get; set; } = string.Empty;
    public string TelNo { get; set; } = string.Empty;
    public string FaxNo { get; set; } = string.Empty;
    public string HomePage { get; set; } = string.Empty;
    public string CoEduType { get; set; } = string.Empty; // 남여공학, 남, 여
    public string FoundationDate { get; set; } = string.Empty;
    public string Anniversary { get; set; } = string.Empty;

    // Badges & Display helpers
    public string DisplayTypeBadge => string.IsNullOrEmpty(SchoolType) ? "학교" : SchoolType;
    public string DisplayFondBadge => string.IsNullOrEmpty(FondType) ? "공립" : FondType;
    public string DisplayShortRegion => string.IsNullOrEmpty(LocationName) ? "" : LocationName.Replace("특별시", "").Replace("광역시", "").Replace("특별자치시", "").Replace("특별자치도", "").Replace("도", "");
}

public class GradeClassCountItem
{
    public string Grade { get; set; } = string.Empty; // "1", "2", ... "특수"
    public string GradeName { get; set; } = string.Empty; // "1학년", "특수학급"
    public int ClassCount { get; set; }
    public double BarWidthPercent { get; set; } = 100.0;
}

public class SchoolScaleDetail
{
    public SchoolSearchResultItem SchoolInfo { get; set; } = new();
    public int AcademicYear { get; set; } = DateTime.Today.Year;
    public int TotalClassCount { get; set; }
    public int SpecialClassCount { get; set; }
    public List<GradeClassCountItem> GradeClasses { get; set; } = new();

    // Scale classification
    public string ScaleCategory { get; set; } = "보통 규모";
    public string ScaleBadgeBg { get; set; } = "#E0E7FF"; // Default Indigo
    public string ScaleBadgeFg { get; set; } = "#3730A3";
    public string ScaleSummaryText { get; set; } = string.Empty;

    // Estimated numbers
    public int EstimatedMinStudents { get; set; }
    public int EstimatedMaxStudents { get; set; }
    public string EstimatedStudentsText => $"{EstimatedMinStudents:N0} ~ {EstimatedMaxStudents:N0}명 (학급당 평균 추산)";

    public string SchoolInfoUrl => $"https://www.schoolinfo.go.kr/ei/ss/PbanplusSearchList.do";
}
