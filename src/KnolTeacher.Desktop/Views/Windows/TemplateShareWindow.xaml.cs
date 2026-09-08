using System;
using System.IO;
using System.Linq;
using System.Windows;
using Microsoft.Win32;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class TemplateShareWindow : Window
{
    private readonly IDataShareService _dataShareService;
    private readonly IStudentManagerService _studentManagerService;
    private readonly IAcademicCalendarService _calendarService;
    private readonly ITimetableService _timetableService;
    private readonly IConfigService _configService;

    public event Action? DataChanged;

    public TemplateShareWindow(
        IDataShareService dataShareService,
        IStudentManagerService studentManagerService,
        IAcademicCalendarService calendarService,
        ITimetableService timetableService,
        IConfigService configService)
    {
        InitializeComponent();
        _dataShareService = dataShareService;
        _studentManagerService = studentManagerService;
        _calendarService = calendarService;
        _timetableService = timetableService;
        _configService = configService;

        UpdateBadges();
    }

    private void UpdateBadges()
    {
        int studentCount = _studentManagerService.Students?.Count ?? 0;
        TxtStudentCountBadge.Text = $"현재 {studentCount}명 등록";
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }

    #region 1. 학생 명렬표
    private void BtnExportStudent_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "학생명렬_양식.csv",
            Title = "학생 명렬표 CSV 양식 다운로드"
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                _dataShareService.ExportStudentRosterTemplate(sfd.FileName);
                ShowStatus($"✅ 학생 명렬표 양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}", false);
            }
            catch (Exception ex)
            {
                ShowStatus($"❌ 저장 실패: {ex.Message}", true);
            }
        }
    }

    private void BtnImportStudent_Click(object sender, RoutedEventArgs e)
    {
        var ofd = new OpenFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv|모든 파일 (*.*)|*.*",
            Title = "학생 명렬표 CSV 가져오기"
        };
        if (ofd.ShowDialog() == true)
        {
            var res = _dataShareService.ImportStudentRosterCsv(ofd.FileName);
            ShowStatus(res.Success ? $"✅ {res.Message}" : $"❌ {res.Message}", !res.Success);
            if (res.Success)
            {
                UpdateBadges();
                DataChanged?.Invoke();
            }
        }
    }
    #endregion

    #region 2. 학사일정 & D-Day
    private void BtnExportSchedule_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "학사일정_D데이_양식.csv",
            Title = "학사일정 & D-Day CSV 양식 다운로드"
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                _dataShareService.ExportAcademicScheduleTemplate(sfd.FileName);
                ShowStatus($"✅ 학사일정 양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}", false);
            }
            catch (Exception ex)
            {
                ShowStatus($"❌ 저장 실패: {ex.Message}", true);
            }
        }
    }

    private void BtnImportSchedule_Click(object sender, RoutedEventArgs e)
    {
        var ofd = new OpenFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv|모든 파일 (*.*)|*.*",
            Title = "학사일정 & D-Day CSV 가져오기"
        };
        if (ofd.ShowDialog() == true)
        {
            var res = _dataShareService.ImportAcademicScheduleCsv(ofd.FileName);
            ShowStatus(res.Success ? $"✅ {res.Message}" : $"❌ {res.Message}", !res.Success);
            if (res.Success)
            {
                DataChanged?.Invoke();
            }
        }
    }
    #endregion

    #region 3. 주간 시간표
    private void BtnExportTimetable_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "주간시간표_양식.csv",
            Title = "주간 시간표 CSV 양식 다운로드"
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                _dataShareService.ExportTimetableTemplate(sfd.FileName);
                ShowStatus($"✅ 주간 시간표 양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}", false);
            }
            catch (Exception ex)
            {
                ShowStatus($"❌ 저장 실패: {ex.Message}", true);
            }
        }
    }

    private void BtnImportTimetable_Click(object sender, RoutedEventArgs e)
    {
        var ofd = new OpenFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv|모든 파일 (*.*)|*.*",
            Title = "주간 시간표 CSV 가져오기"
        };
        if (ofd.ShowDialog() == true)
        {
            var res = _dataShareService.ImportTimetableCsv(ofd.FileName);
            ShowStatus(res.Success ? $"✅ {res.Message}" : $"❌ {res.Message}", !res.Success);
            if (res.Success)
            {
                DataChanged?.Invoke();
            }
        }
    }
    #endregion

    #region 4. 맞춤 설정 패키지
    private void BtnExportFullConfig_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "놀티쳐 설정 패키지 (*.knolcfg)|*.knolcfg|JSON 파일 (*.json)|*.json",
            FileName = "놀티쳐_맞춤설정_공유.knolcfg",
            Title = "놀티쳐 설정 공유 패키지 내보내기"
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                _dataShareService.ExportFullConfigPackage(sfd.FileName);
                ShowStatus($"✅ 놀티쳐 설정 패키지가 저장되었습니다: {Path.GetFileName(sfd.FileName)}", false);
            }
            catch (Exception ex)
            {
                ShowStatus($"❌ 저장 실패: {ex.Message}", true);
            }
        }
    }

    private void BtnImportFullConfig_Click(object sender, RoutedEventArgs e)
    {
        var ofd = new OpenFileDialog
        {
            Filter = "놀티쳐 설정 패키지 (*.knolcfg)|*.knolcfg|JSON 파일 (*.json)|*.json|모든 파일 (*.*)|*.*",
            Title = "놀티쳐 설정 패키지 불러오기"
        };
        if (ofd.ShowDialog() == true)
        {
            var res = _dataShareService.ImportFullConfigPackage(ofd.FileName);
            ShowStatus(res.Success ? $"✅ {res.Message}" : $"❌ {res.Message}", !res.Success);
            if (res.Success)
            {
                UpdateBadges();
                DataChanged?.Invoke();
            }
        }
    }
    #endregion

    #region Drag & Drop
    private void Window_DragOver(object sender, DragEventArgs e)
    {
        if (e.Data.GetDataPresent(DataFormats.FileDrop))
        {
            e.Effects = DragDropEffects.Copy;
        }
        else
        {
            e.Effects = DragDropEffects.None;
        }
        e.Handled = true;
    }

    private void Window_Drop(object sender, DragEventArgs e)
    {
        if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;

        var files = e.Data.GetData(DataFormats.FileDrop) as string[];
        if (files == null || files.Length == 0) return;

        string file = files[0];
        string ext = Path.GetExtension(file).ToLowerInvariant();

        if (ext == ".knolcfg" || (ext == ".json" && file.Contains("설정")))
        {
            var res = _dataShareService.ImportFullConfigPackage(file);
            ShowStatus(res.Success ? $"✅ {res.Message}" : $"❌ {res.Message}", !res.Success);
            if (res.Success)
            {
                UpdateBadges();
                DataChanged?.Invoke();
            }
            return;
        }

        if (ext == ".csv")
        {
            try
            {
                string firstLine = File.ReadLines(file).FirstOrDefault() ?? "";
                if (firstLine.Contains("교시") || firstLine.Contains("월") || firstLine.Contains("화"))
                {
                    var res = _dataShareService.ImportTimetableCsv(file);
                    ShowStatus($"⏰ {res.Message}", !res.Success);
                    if (res.Success) DataChanged?.Invoke();
                }
                else if (firstLine.Contains("학사") || firstLine.Contains("휴업") || firstLine.Contains("D데이") || firstLine.Contains("날짜"))
                {
                    var res = _dataShareService.ImportAcademicScheduleCsv(file);
                    ShowStatus($"📅 {res.Message}", !res.Success);
                    if (res.Success) DataChanged?.Invoke();
                }
                else
                {
                    var res = _dataShareService.ImportStudentRosterCsv(file);
                    ShowStatus($"🎓 {res.Message}", !res.Success);
                    if (res.Success)
                    {
                        UpdateBadges();
                        DataChanged?.Invoke();
                    }
                }
            }
            catch (Exception ex)
            {
                ShowStatus($"❌ 파일 처리 오류: {ex.Message}", true);
            }
        }
    }
    #endregion

    private void ShowStatus(string msg, bool isError)
    {
        TxtStatusMessage.Text = msg;
        TxtStatusMessage.Foreground = isError
            ? System.Windows.Media.Brushes.Crimson
            : (System.Windows.Media.Brush)FindResource("BeigeAccent");
    }
}
