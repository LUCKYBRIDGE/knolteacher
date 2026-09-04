using System;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class SchoolScaleWindow : Window
{
    private readonly ISchoolScaleService _scaleService;
    private readonly IConfigService _configService;
    private SchoolSearchResultItem? _currentSchool;
    private SchoolScaleDetail? _currentDetail;

    public SchoolScaleWindow(ISchoolScaleService scaleService, IConfigService configService)
    {
        InitializeComponent();
        _scaleService = scaleService;
        _configService = configService;

        TbSchoolQuery.TextChanged += (s, e) =>
        {
            TbWatermark.Visibility = string.IsNullOrEmpty(TbSchoolQuery.Text) ? Visibility.Visible : Visibility.Collapsed;
        };

        Closing += (s, e) =>
        {
            e.Cancel = true;
            Hide();
        };

        Loaded += SchoolScaleWindow_Loaded;
    }

    private void SchoolScaleWindow_Loaded(object sender, RoutedEventArgs e)
    {
        // If config already has a school, prefill search box
        var cfg = _configService.NeisConfig;
        if (!string.IsNullOrEmpty(cfg.SchoolName) && string.IsNullOrEmpty(TbSchoolQuery.Text))
        {
            TbSchoolQuery.Text = cfg.SchoolName;
            _ = ExecuteSearchAsync();
        }
    }

    private void TbSchoolQuery_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            _ = ExecuteSearchAsync();
        }
    }

    private void BtnSearch_Click(object sender, RoutedEventArgs e)
    {
        _ = ExecuteSearchAsync();
    }

    private async Task ExecuteSearchAsync()
    {
        string query = TbSchoolQuery.Text.Trim();
        if (string.IsNullOrWhiteSpace(query))
        {
            MessageBox.Show("조회할 학교 이름을 입력해 주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        string officeCode = "ALL";
        if (ComboOffice.SelectedItem is ComboBoxItem cbi && cbi.Tag is string tag)
        {
            officeCode = tag;
        }

        TxtResultCount.Text = "검색 중...";
        ListSearchResults.ItemsSource = null;
        PanelEmptyState.Visibility = Visibility.Visible;
        ScrollDetailContent.Visibility = Visibility.Collapsed;
        PanelLoading.Visibility = Visibility.Collapsed;

        var results = await _scaleService.SearchSchoolsAsync(query, officeCode);

        TxtResultCount.Text = $"검색 결과 ({results.Count}개)";
        ListSearchResults.ItemsSource = results;

        if (results.Count == 0)
        {
            PanelEmptyState.Visibility = Visibility.Visible;
            ScrollDetailContent.Visibility = Visibility.Collapsed;
            MessageBox.Show($"'{query}'에 해당하는 학교를 찾을 수 없습니다.\n교육청 필터나 학교 이름을 다시 확인해 주세요.", "검색 결과 없음", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        else
        {
            // Auto-select first item
            ListSearchResults.SelectedIndex = 0;
        }
    }

    private async void ListSearchResults_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ListSearchResults.SelectedItem is not SchoolSearchResultItem item) return;

        _currentSchool = item;
        PanelEmptyState.Visibility = Visibility.Collapsed;
        ScrollDetailContent.Visibility = Visibility.Collapsed;
        PanelLoading.Visibility = Visibility.Visible;

        var detail = await _scaleService.GetSchoolScaleDetailAsync(item);
        PanelLoading.Visibility = Visibility.Collapsed;

        if (detail == null)
        {
            PanelEmptyState.Visibility = Visibility.Visible;
            return;
        }

        _currentDetail = detail;
        PopulateDetail(detail);
        ScrollDetailContent.Visibility = Visibility.Visible;
    }

    private void PopulateDetail(SchoolScaleDetail detail)
    {
        var sch = detail.SchoolInfo;
        TxtDetailSchoolName.Text = sch.SchoolName;
        TxtDetailOffice.Text = string.IsNullOrEmpty(sch.OfficeName) ? "교육청" : sch.OfficeName;
        TxtDetailJurisdiction.Text = string.IsNullOrEmpty(sch.JurisdictionName) ? "직속" : sch.JurisdictionName;
        TxtDetailFondCoEdu.Text = $"{sch.DisplayFondBadge} · {(string.IsNullOrEmpty(sch.CoEduType) ? "남여공학" : sch.CoEduType)}";

        // Scale Badge
        TxtScaleBadge.Text = detail.ScaleCategory;
        try
        {
            var brush = (Brush)new BrushConverter().ConvertFromString(detail.ScaleBadgeBg)!;
            BorderScaleBadge.Background = brush;
            var fgBrush = (Brush)new BrushConverter().ConvertFromString(detail.ScaleBadgeFg)!;
            TxtScaleBadge.Foreground = fgBrush;
        }
        catch { }

        TxtScaleSummary.Text = detail.ScaleSummaryText;

        // KPI cards
        TxtTotalClassCount.Text = $"{detail.TotalClassCount} 학급";
        int normalClasses = Math.Max(0, detail.TotalClassCount - detail.SpecialClassCount);
        TxtSpecialClassCount.Text = detail.SpecialClassCount > 0
            ? $"일반 {normalClasses} + 특수 {detail.SpecialClassCount}"
            : $"일반 {normalClasses}학급 (특수학급 없음)";

        TxtEstimatedStudents.Text = detail.EstimatedStudentsText;

        // Foundation Date
        string fond = sch.FoundationDate;
        if (!string.IsNullOrEmpty(fond) && fond.Length == 8)
        {
            TxtFoundationDate.Text = $"{fond[..4]}. {fond.Substring(4, 2)}. {fond.Substring(6, 2)}";
        }
        else
        {
            TxtFoundationDate.Text = string.IsNullOrEmpty(fond) ? "정보 없음" : fond;
        }

        string anni = sch.Anniversary;
        if (!string.IsNullOrEmpty(anni) && anni.Length == 8)
        {
            TxtAnniversary.Text = $"개교기념일: {anni.Substring(4, 2)}월 {anni.Substring(6, 2)}일";
        }
        else
        {
            TxtAnniversary.Text = string.IsNullOrEmpty(anni) ? "개교기념일: 정보 없음" : $"개교기념일: {anni}";
        }

        // Grade-by-grade breakdown
        TxtBreakdownTitle.Text = $"📊 학년별 학급 편성 현황 ({detail.AcademicYear}학년도 기준)";
        ListGradeClasses.ItemsSource = detail.GradeClasses;

        // Contact info
        TxtRoadAddress.Text = string.IsNullOrEmpty(sch.RoadAddress) ? "주소 정보 없음" : sch.RoadAddress;
        TxtTelNo.Text = string.IsNullOrEmpty(sch.TelNo) ? "전화번호 미등록" : sch.TelNo;
        TxtFaxNo.Text = string.IsNullOrEmpty(sch.FaxNo) ? "팩스번호 미등록" : sch.FaxNo;
        TxtHomePage.Text = string.IsNullOrEmpty(sch.HomePage) ? "홈페이지 미등록" : sch.HomePage;
    }

    private void TxtHomePage_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        string url = TxtHomePage.Text;
        if (!string.IsNullOrEmpty(url) && (url.StartsWith("http://") || url.StartsWith("https://")))
        {
            try
            {
                Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true });
            }
            catch { }
        }
    }

    private void BtnSetDefaultSchool_Click(object sender, RoutedEventArgs e)
    {
        if (_currentSchool == null) return;

        var cfg = _configService.NeisConfig;
        cfg.OfficeCode = _currentSchool.OfficeCode;
        cfg.OfficeName = _currentSchool.OfficeName;
        cfg.SchoolCode = _currentSchool.SchoolCode;
        cfg.SchoolName = _currentSchool.SchoolName;
        cfg.SchoolType = _currentSchool.SchoolType;
        if (_currentDetail != null)
        {
            cfg.AcademicYear = _currentDetail.AcademicYear.ToString();
        }
        _configService.SaveNeisConfig();

        MessageBox.Show(
            $"🌟 '{_currentSchool.SchoolName}'이(가) 놀티쳐 기본 학교로 설정되었습니다!\n\n" +
            "메인 화면의 오늘의 급식 식단표 및 시간표가 해당 학교로 자동 연동됩니다.",
            "놀티쳐 학교 설정 완료",
            MessageBoxButton.OK,
            MessageBoxImage.Information);
    }

    private void BtnOpenSchoolInfo_Click(object sender, RoutedEventArgs e)
    {
        if (_currentSchool == null) return;

        string targetUrl = $"https://www.schoolinfo.go.kr/ei/ss/PbanplusSearchList.do";
        try
        {
            Process.Start(new ProcessStartInfo { FileName = targetUrl, UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show($"학교알리미 웹사이트를 여는 중 오류가 발생했습니다: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void BtnCopyInfo_Click(object sender, RoutedEventArgs e)
    {
        if (_currentSchool == null || _currentDetail == null) return;

        var sb = new StringBuilder();
        sb.AppendLine($"[학교 정보 및 규모 통계]");
        sb.AppendLine($"🏫 학교명: {_currentSchool.SchoolName}");
        sb.AppendLine($"🏛️ 관할: {_currentSchool.OfficeName} ({_currentSchool.JurisdictionName})");
        sb.AppendLine($"🏷️ 구분: {_currentSchool.DisplayFondBadge} · {_currentSchool.SchoolType} ({_currentSchool.CoEduType})");
        sb.AppendLine($"📅 개교: {TxtFoundationDate.Text} ({TxtAnniversary.Text})");
        sb.AppendLine($"📚 학급 규모: 총 {_currentDetail.TotalClassCount}학급 ({_currentDetail.ScaleCategory})");

        var gradeStr = string.Join(", ", _currentDetail.GradeClasses.Select(g => $"{g.GradeName} {g.ClassCount}학급"));
        sb.AppendLine($"📊 학년별 편성: {gradeStr}");
        sb.AppendLine($"👥 예상 학생수: {_currentDetail.EstimatedStudentsText}");
        sb.AppendLine($"📍 도로명주소: {_currentSchool.RoadAddress}");
        sb.AppendLine($"📞 전화: {_currentSchool.TelNo} / 📠 팩스: {_currentSchool.FaxNo}");
        sb.AppendLine($"🌐 홈페이지: {_currentSchool.HomePage}");

        try
        {
            Clipboard.SetText(sb.ToString());
            MessageBox.Show("학교 정보 및 규모 통계가 클립보드에 복사되었습니다!\n한글(HWP)이나 메신저에 붙여넣기(Ctrl+V) 하실 수 있습니다.", "복사 완료", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"클립보드 복사 중 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
