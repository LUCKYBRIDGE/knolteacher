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
        UpdateApiKeyBadge();

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
        GridDetailView.Visibility = Visibility.Collapsed;
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
        GridDetailView.Visibility = Visibility.Visible;
        SwitchToStatsView();
        _ = UpdateMapForCurrentSchoolAsync();
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

    private void UpdateApiKeyBadge()
    {
        string key = _configService.NeisConfig?.ApiKey?.Trim() ?? string.Empty;
        if (!string.IsNullOrEmpty(key))
        {
            string masked = key.Length > 8 ? $"{key.Substring(0, 4)}...{key.Substring(key.Length - 4)}" : key;
            TxtApiKeyStatus.Text = $"인증 활성화 ({masked})";
            BadgeApiKeyStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DCFCE7"));
            BadgeApiKeyStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#86EFAC"));
            TxtApiKeyStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#15803D"));
            BadgeApiKeyStatus.ToolTip = $"등록된 인증키: {key}\n(쿼리 제한 해제 및 초고속 정밀 API 응답 적용 중)";
        }
        else
        {
            TxtApiKeyStatus.Text = "공공 기본 모드 (키 미등록)";
            BadgeApiKeyStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEF3C7"));
            BadgeApiKeyStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE68A"));
            TxtApiKeyStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B45309"));
            BadgeApiKeyStatus.ToolTip = "클릭하여 교육정보 개방포털에서 발급받은 개인 API 키를 등록할 수 있습니다.";
        }
    }

    private void BtnConfigApiKey_Click(object sender, RoutedEventArgs e)
    {
        string currentKey = _configService.NeisConfig?.ApiKey ?? string.Empty;
        var dlg = new PromptInputDialog(
            "나이스(NEIS) 오픈 API 인증키 설정",
            "교육정보 개방포털(open.neis.go.kr)에서 발급받으신 인증키를 입력해주세요:\n(인증키 등록 시 호출 제한 해제 및 초고속 데이터 조회가 적용됩니다)",
            currentKey)
        {
            Owner = this
        };

        if (dlg.ShowDialog() == true)
        {
            if (_configService.NeisConfig == null)
            {
                _configService.NeisConfig = new NeisConfig();
            }
            _configService.NeisConfig.ApiKey = dlg.InputText.Trim();
            _configService.SaveNeisConfig();
            UpdateApiKeyBadge();
            MessageBox.Show("나이스 API 인증키가 안전하게 저장되었습니다!", "API 키 설정 완료", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void BtnTabStats_Click(object sender, RoutedEventArgs e)
    {
        SwitchToStatsView();
    }

    private void BtnTabMap_Click(object sender, RoutedEventArgs e)
    {
        SwitchToMapView();
        _ = UpdateMapForCurrentSchoolAsync();
    }

    private void SwitchToStatsView()
    {
        if (ScrollDetailContent != null) ScrollDetailContent.Visibility = Visibility.Visible;
        if (PanelMapView != null) PanelMapView.Visibility = Visibility.Collapsed;
        if (BtnTabStats != null)
        {
            BtnTabStats.Background = (Brush)FindResource("BeigeAccent");
            BtnTabStats.Foreground = Brushes.White;
        }
        if (BtnTabMap != null)
        {
            BtnTabMap.Background = (Brush)FindResource("BeigeCardInner");
            BtnTabMap.Foreground = (Brush)FindResource("BeigeTextMain");
        }
    }

    private void SwitchToMapView()
    {
        if (ScrollDetailContent != null) ScrollDetailContent.Visibility = Visibility.Collapsed;
        if (PanelMapView != null) PanelMapView.Visibility = Visibility.Visible;
        if (BtnTabMap != null)
        {
            BtnTabMap.Background = (Brush)FindResource("BeigeAccent");
            BtnTabMap.Foreground = Brushes.White;
        }
        if (BtnTabStats != null)
        {
            BtnTabStats.Background = (Brush)FindResource("BeigeCardInner");
            BtnTabStats.Foreground = (Brush)FindResource("BeigeTextMain");
        }
    }

    private void BtnOpenKakaoMap_Click(object sender, RoutedEventArgs e)
    {
        if (_currentSchool == null) return;
        string query = Uri.EscapeDataString($"{_currentSchool.SchoolName} {_currentSchool.RoadAddress}".Trim());
        try
        {
            Process.Start(new ProcessStartInfo { FileName = $"https://map.kakao.com/link/search/{query}", UseShellExecute = true });
        }
        catch { }
    }

    private void BtnOpenNaverMap_Click(object sender, RoutedEventArgs e)
    {
        if (_currentSchool == null) return;
        string query = Uri.EscapeDataString($"{_currentSchool.SchoolName}".Trim());
        try
        {
            Process.Start(new ProcessStartInfo { FileName = $"https://map.naver.com/v5/search/{query}", UseShellExecute = true });
        }
        catch { }
    }

    private async Task UpdateMapForCurrentSchoolAsync()
    {
        if (_currentSchool == null || MapWebView == null) return;

        try
        {
            await MapWebView.EnsureCoreWebView2Async();
        }
        catch { return; }

        double lat = 37.5665;
        double lon = 126.9780;

        // Fallback coordinates by Education Office Code
        lat = _currentSchool.OfficeCode switch
        {
            "B10" => 37.5665, // 서울
            "C10" => 35.1796, // 부산
            "D10" => 35.8714, // 대구
            "E10" => 37.4563, // 인천
            "F10" => 35.1595, // 광주
            "G10" => 36.3504, // 대전
            "H10" => 35.5384, // 울산
            "I10" => 36.4800, // 세종
            "J10" => 37.2636, // 경기
            "K10" => 37.8854, // 강원
            "M10" => 36.6424, // 충북
            "N10" => 36.6588, // 충남
            "P10" => 35.8242, // 전북
            "Q10" => 34.8161, // 전남
            "R10" => 36.5760, // 경북
            "S10" => 35.2383, // 경남
            "T10" => 33.4996, // 제주
            _ => 37.5665
        };

        lon = _currentSchool.OfficeCode switch
        {
            "B10" => 126.9780,
            "C10" => 129.0756,
            "D10" => 128.6014,
            "E10" => 126.7052,
            "F10" => 126.8526,
            "G10" => 127.3845,
            "H10" => 129.3114,
            "I10" => 127.2890,
            "J10" => 127.0286,
            "K10" => 127.7298,
            "M10" => 127.4890,
            "N10" => 126.6728,
            "P10" => 127.1480,
            "Q10" => 126.4629,
            "R10" => 128.5056,
            "S10" => 128.6922,
            "T10" => 126.5312,
            _ => 126.9780
        };

        // Try geocoding with OpenStreetMap Nominatim
        if (!string.IsNullOrWhiteSpace(_currentSchool.RoadAddress))
        {
            try
            {
                using var client = new System.Net.Http.HttpClient { Timeout = TimeSpan.FromSeconds(2) };
                client.DefaultRequestHeaders.UserAgent.ParseAdd("KnolTeacher/3.0");
                string query = Uri.EscapeDataString(_currentSchool.RoadAddress);
                string geoJson = await client.GetStringAsync($"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1");
                using var doc = System.Text.Json.JsonDocument.Parse(geoJson);
                if (doc.RootElement.GetArrayLength() > 0)
                {
                    var first = doc.RootElement[0];
                    if (first.TryGetProperty("lat", out var latProp) && double.TryParse(latProp.GetString(), out double parsedLat))
                    {
                        lat = parsedLat;
                    }
                    if (first.TryGetProperty("lon", out var lonProp) && double.TryParse(lonProp.GetString(), out double parsedLon))
                    {
                        lon = parsedLon;
                    }
                }
            }
            catch { }
        }

        string schoolName = System.Web.HttpUtility.HtmlEncode(_currentSchool.SchoolName);
        string address = System.Web.HttpUtility.HtmlEncode(_currentSchool.RoadAddress);
        string tel = System.Web.HttpUtility.HtmlEncode(_currentSchool.TelNo);
        string scaleCategory = _currentDetail != null ? System.Web.HttpUtility.HtmlEncode(_currentDetail.ScaleCategory) : "";
        string totalClasses = _currentDetail != null ? _currentDetail.TotalClassCount.ToString() : "";
        string students = _currentDetail != null ? System.Web.HttpUtility.HtmlEncode(_currentDetail.EstimatedStudentsText) : "";

        string html = $@"<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' />
    <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
    <style>
        html, body, #map {{ height: 100%; margin: 0; padding: 0; font-family: 'Malgun Gothic', sans-serif; }}
        .custom-pin {{
            background-color: #0284C7;
            color: white;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.35);
            border: 2px solid white;
        }}
        .popup-box {{
            padding: 4px;
            font-size: 12px;
            line-height: 1.6;
        }}
        .popup-title {{
            font-size: 15px;
            font-weight: bold;
            color: #0F172A;
            margin-bottom: 4px;
        }}
        .badge {{
            display: inline-block;
            background: #E0F2FE;
            color: #0369A1;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
            margin-right: 4px;
        }}
    </style>
</head>
<body>
    <div id='map'></div>
    <script>
        var map = L.map('map').setView([{lat}, {lon}], 16);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }}).addTo(map);

        var pin = L.divIcon({{
            className: 'custom-pin',
            html: '🏫',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        }});

        var marker = L.marker([{lat}, {lon}], {{ icon: pin }}).addTo(map);
        marker.bindPopup(`
            <div class='popup-box'>
                <div class='popup-title'>{schoolName}</div>
                <div style='margin-bottom:6px;'>
                    <span class='badge'>{scaleCategory}</span>
                    <span class='badge'>총 {totalClasses}학급</span>
                </div>
                <div><b>예상 학생수:</b> {students}</div>
                <div><b>주소:</b> {address}</div>
                <div><b>전화:</b> {tel}</div>
            </div>
        `).openPopup();
    </script>
</body>
</html>";

        MapWebView.NavigateToString(html);
    }
}
