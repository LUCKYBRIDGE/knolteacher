using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using Microsoft.Win32;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public class StatusHighlightConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        string? current = value as string;
        string? target = parameter as string;

        if (current == target)
        {
            return target switch
            {
                "Completed" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669")), // Emerald
                "Pending" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#D97706")),   // Amber
                _ => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DC2626"))            // Red
            };
        }

        return new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")); // Dark slate
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) => Binding.DoNothing;
}

public partial class ClassroomHubWindow : Window
{
    private readonly IStudentManagerService _studentService;
    private readonly IClassroomRecordService _recordService;
    private readonly IConfigService? _configService;

    private ObservableCollection<StudentItem> _rosterStudents = new();
    private ChecklistGroup? _selectedChecklist;
    private string _checklistCategoryFilter = "전체";

    public ClassroomHubWindow(IStudentManagerService studentService, IClassroomRecordService recordService, IConfigService? configService = null)
    {
        InitializeComponent();
        _studentService = studentService;
        _recordService = recordService;
        _configService = configService;

        Closing += (s, e) =>
        {
            e.Cancel = true;
            Hide();
        };

        Loaded += ClassroomHubWindow_Loaded;
    }

    public void RefreshAll()
    {
        LoadRosterTab();
        LoadChecklistTab();
        LoadCumulativeTab();
    }

    private void ClassroomHubWindow_Loaded(object sender, RoutedEventArgs e)
    {
        RefreshAll();
    }

    public void SelectTab(int tabIndex)
    {
        if (HubTabs != null && tabIndex >= 0 && tabIndex < HubTabs.Items.Count)
        {
            HubTabs.SelectedIndex = tabIndex;
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Hide();
    }

    #region ================== 1. 학생 명렬표 (Roster) ==================

    private void LoadRosterTab()
    {
        _rosterStudents = new ObservableCollection<StudentItem>(_studentService.Students);
        GridStudents.ItemsSource = _rosterStudents;
        UpdateRosterCountBadge();
    }

    private void UpdateRosterCountBadge()
    {
        TxtRosterCountBadge.Text = $"총 {_rosterStudents.Count}명 등록";
    }

    private void BtnOpenPasteRoster_Click(object sender, RoutedEventArgs e)
    {
        TbPastedRosterText.Text = string.Empty;
        PasteOverlay.Visibility = Visibility.Visible;
    }

    private void BtnClosePaste_Click(object sender, RoutedEventArgs e)
    {
        PasteOverlay.Visibility = Visibility.Collapsed;
    }

    private void BtnApplyPastedRoster_Click(object sender, RoutedEventArgs e)
    {
        string text = TbPastedRosterText.Text;
        if (string.IsNullOrWhiteSpace(text))
        {
            MessageBox.Show("붙여넣은 학생 명단 텍스트가 없습니다.", "알림", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var parsed = _recordService.ParsePastedRosterText(text);
        if (parsed.Count == 0)
        {
            MessageBox.Show("학생 이름을 인식하지 못했습니다. 한 줄에 한 명씩 이름을 입력해주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        _studentService.Students.Clear();
        _studentService.Students.AddRange(parsed);
        _studentService.SaveRoster();

        LoadRosterTab();
        PasteOverlay.Visibility = Visibility.Collapsed;

        // Sync to dropdowns
        InitCumulativeDropdowns();

        HudNotificationWindow.Instance.ShowToast("👥", $"{parsed.Count}명의 학생 명렬표가 새롭게 등록되었습니다.");
    }

    private void BtnShuffleAvatars_Click(object sender, RoutedEventArgs e)
    {
        var rnd = new Random();
        foreach (var student in _rosterStudents)
        {
            int idx = rnd.Next(1, 33);
            student.AvatarId = $"avatar_{idx:D2}";
        }

        _studentService.Students.Clear();
        _studentService.Students.AddRange(_rosterStudents);
        _studentService.SaveRoster();

        GridStudents.Items.Refresh();
        HudNotificationWindow.Instance.ShowToast("🎲", "32종 동물 아바타가 학생들에게 랜덤 배정되었습니다.");
    }

    private void BtnAddStudentRow_Click(object sender, RoutedEventArgs e)
    {
        int nextNum = _rosterStudents.Count == 0 ? 1 : _rosterStudents.Max(s => s.Number) + 1;
        var newStudent = new StudentItem
        {
            Number = nextNum,
            Name = $"학생 {nextNum}",
            Gender = "남",
            AvatarId = $"avatar_{(nextNum - 1) % 32 + 1:D2}"
        };

        _rosterStudents.Add(newStudent);
        UpdateRosterCountBadge();
    }

    private void BtnDeleteStudentRow_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is StudentItem student)
        {
            if (MessageBox.Show($"{student.Number}번 {student.Name} 학생을 명렬표에서 삭제하시겠습니까?", "확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                _rosterStudents.Remove(student);
                UpdateRosterCountBadge();
            }
        }
    }

    private void BtnChangeAvatar_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is StudentItem student)
        {
            // Cycle avatar
            int currentNum = 1;
            if (student.AvatarId.StartsWith("avatar_") && int.TryParse(student.AvatarId[7..], out int parsed))
            {
                currentNum = parsed;
            }
            int nextIdx = (currentNum % 32) + 1;
            student.AvatarId = $"avatar_{nextIdx:D2}";

            GridStudents.Items.Refresh();
        }
    }

    private void BtnDownloadRosterTemplate_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "학생명렬표_표준양식.csv",
            Title = "학생 명렬표 표준 양식 다운로드",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                string csv = _recordService.GetRosterCsvTemplate();
                _recordService.ExportCsvFile(sfd.FileName, csv);
                HudNotificationWindow.Instance.ShowToast("📄", $"명렬표 양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"양식 저장 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnExportRosterCsv_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = $"학생명렬표_{DateTime.Now:yyyyMMdd}.csv",
            Title = "학생 명렬표 CSV 내보내기",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                var sb = new StringBuilder();
                sb.AppendLine("번호,이름,성별,1인1역,생년월일,보호자연락처,특이사항메모");
                foreach (var s in _rosterStudents.OrderBy(s => s.Number))
                {
                    sb.AppendLine($"{s.Number},{s.Name},{s.Gender},{s.Role},{s.BirthDate},{s.Contact},\"{s.Note.Replace("\"", "\"\"")}\"");
                }
                _recordService.ExportCsvFile(sfd.FileName, sb.ToString());
                HudNotificationWindow.Instance.ShowToast("💾", $"명렬표가 내보내졌습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"내보내기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnImportRosterCsv_Click(object sender, RoutedEventArgs e)
    {
        var ofd = new OpenFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv|모든 파일 (*.*)|*.*",
            Title = "학생 명렬표 CSV 파일 열기"
        };
        if (ofd.ShowDialog() == true)
        {
            try
            {
                var lines = File.ReadAllLines(ofd.FileName, Encoding.Default);
                if (lines.Length <= 1)
                {
                    lines = File.ReadAllLines(ofd.FileName, Encoding.UTF8);
                }

                var imported = new List<StudentItem>();
                bool isHeader = true;
                foreach (var line in lines)
                {
                    if (string.IsNullOrWhiteSpace(line)) continue;
                    if (isHeader)
                    {
                        isHeader = false;
                        if (line.Contains("번호") || line.Contains("이름")) continue;
                    }

                    var parts = line.Split(',');
                    if (parts.Length >= 2)
                    {
                        int.TryParse(parts[0].Trim(), out int num);
                        string name = parts[1].Trim();
                        string gender = parts.Length > 2 ? parts[2].Trim() : string.Empty;
                        string role = parts.Length > 3 ? parts[3].Trim() : string.Empty;
                        string birth = parts.Length > 4 ? parts[4].Trim() : string.Empty;
                        string contact = parts.Length > 5 ? parts[5].Trim() : string.Empty;
                        string note = parts.Length > 6 ? parts[6].Trim().Trim('"') : string.Empty;

                        imported.Add(new StudentItem
                        {
                            Number = num == 0 ? imported.Count + 1 : num,
                            Name = name,
                            Gender = gender,
                            Role = role,
                            BirthDate = birth,
                            Contact = contact,
                            Note = note,
                            AvatarId = $"avatar_{(imported.Count) % 32 + 1:D2}"
                        });
                    }
                }

                if (imported.Count > 0)
                {
                    _studentService.Students.Clear();
                    _studentService.Students.AddRange(imported);
                    _studentService.SaveRoster();
                    LoadRosterTab();
                    InitCumulativeDropdowns();
                    HudNotificationWindow.Instance.ShowToast("📂", $"{imported.Count}명의 학생 명렬을 가져왔습니다.");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"CSV 가져오기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnSaveRoster_Click(object sender, RoutedEventArgs e)
    {
        _studentService.Students.Clear();
        _studentService.Students.AddRange(_rosterStudents);
        _studentService.SaveRoster();
        InitCumulativeDropdowns();
        HudNotificationWindow.Instance.ShowToast("💾", "학생 명렬표가 저장되었습니다.");
    }

    #endregion

    #region ================== 2. 체크리스트 (Checklist) ==================

    private void LoadChecklistTab()
    {
        RefreshChecklistCatalog();

        if (_selectedChecklist == null && _recordService.Checklists.Count > 0)
        {
            SelectChecklist(_recordService.Checklists[0]);
        }
        else if (_recordService.Checklists.Count == 0)
        {
            // Seed a sample checklist
            var sample = _recordService.CreateChecklist("1학기 수학익힘책 34~35쪽 검사", "과제", _studentService.Students);
            SelectChecklist(sample);
            RefreshChecklistCatalog();
        }
    }

    private void RefreshChecklistCatalog()
    {
        var filtered = _checklistCategoryFilter == "전체"
            ? _recordService.Checklists
            : _recordService.Checklists.Where(c => c.Category == _checklistCategoryFilter).ToList();

        ListChecklists.ItemsSource = null;
        ListChecklists.ItemsSource = filtered;

        if (_selectedChecklist != null && filtered.Contains(_selectedChecklist))
        {
            ListChecklists.SelectedItem = _selectedChecklist;
        }
    }

    private void BtnFilterChecklist_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string cat)
        {
            _checklistCategoryFilter = cat;
            RefreshChecklistCatalog();
        }
    }

    private void ListChecklists_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ListChecklists.SelectedItem is ChecklistGroup group)
        {
            SelectChecklist(group);
        }
    }

    private void SelectChecklist(ChecklistGroup group)
    {
        _selectedChecklist = group;
        TxtSelectedChecklistTitle.Text = $"[{group.Category}] {group.Title}";
        TxtSelectedChecklistSub.Text = $"점검 일자: {group.TargetDate}  •  학생별 O(완료), △(보완), X(미제출)를 클릭하세요.";

        UpdateChecklistProgress();
        ItemsChecklistStudents.ItemsSource = null;
        ItemsChecklistStudents.ItemsSource = group.Items.OrderBy(i => i.StudentNumber).ToList();
    }

    private void UpdateChecklistProgress()
    {
        if (_selectedChecklist == null) return;

        int total = _selectedChecklist.TotalCount;
        int completed = _selectedChecklist.CompletedCount;
        int rate = _selectedChecklist.CompletionRate;

        TxtChecklistStats.Text = $"{completed}/{total}명 완료 ({rate}%)";
        PbChecklistProgress.Value = rate;
    }

    private void BtnNewChecklist_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PromptInputDialog("새 체크리스트 생성", "체크리스트 제목을 입력하세요:", $"과제 점검 ({DateTime.Today:MM/dd})");
        dlg.Owner = this;
        if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
        {
            var created = _recordService.CreateChecklist(dlg.InputText, "과제", _studentService.Students);
            RefreshChecklistCatalog();
            SelectChecklist(created);
            HudNotificationWindow.Instance.ShowToast("📋", $"새 체크리스트 '{dlg.InputText}'(이)가 생성되었습니다.");
        }
    }

    private void BtnDeleteChecklist_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string id)
        {
            if (MessageBox.Show("선택한 체크리스트를 삭제하시겠습니까?", "확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                _recordService.DeleteChecklist(id);
                _selectedChecklist = _recordService.Checklists.FirstOrDefault();
                RefreshChecklistCatalog();
                if (_selectedChecklist != null) SelectChecklist(_selectedChecklist);
            }
        }
    }

    private void BtnItemStatus_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedChecklist == null) return;
        if (sender is Button btn && btn.Tag is string newStatus && btn.DataContext is ChecklistItem item)
        {
            _recordService.SetChecklistItemStatus(_selectedChecklist.Id, item.StudentNumber, newStatus);
            UpdateChecklistProgress();
            ItemsChecklistStudents.Items.Refresh();
            ListChecklists.Items.Refresh();
        }
    }

    private void BtnSetAllStatus_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedChecklist == null) return;
        if (sender is Button btn && btn.Tag is string targetStatus)
        {
            foreach (var item in _selectedChecklist.Items)
            {
                item.Status = targetStatus;
            }
            _recordService.SaveChecklists();
            UpdateChecklistProgress();
            ItemsChecklistStudents.Items.Refresh();
            ListChecklists.Items.Refresh();
        }
    }

    private void BtnCopyUncompleted_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedChecklist == null) return;
        string summary = _selectedChecklist.GetUncompletedSummary();
        Clipboard.SetText(summary);
        HudNotificationWindow.Instance.ShowToast("📋", "미제출자 명단이 클립보드에 복사되었습니다.");
    }

    private void BtnDownloadChecklistTemplate_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "체크리스트_표준양식.csv",
            Title = "체크리스트 표준 양식 다운로드",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                string csv = _recordService.GetChecklistCsvTemplate(_selectedChecklist);
                _recordService.ExportCsvFile(sfd.FileName, csv);
                HudNotificationWindow.Instance.ShowToast("📄", $"양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"양식 저장 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnExportChecklistCsv_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedChecklist == null) return;
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = $"체크리스트_{_selectedChecklist.Title}_{DateTime.Now:yyyyMMdd}.csv",
            Title = "체크리스트 CSV 내보내기",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                string csv = _recordService.GetChecklistCsvTemplate(_selectedChecklist);
                _recordService.ExportCsvFile(sfd.FileName, csv);
                HudNotificationWindow.Instance.ShowToast("💾", $"체크리스트가 내보내졌습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"내보내기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    #endregion

    #region ================== 3. 누가기록 & 관찰일지 (Cumulative Records) ==================

    private void LoadCumulativeTab()
    {
        InitCumulativeDropdowns();
        DpRecordDate.SelectedDate = DateTime.Today;

        RefreshCumulativeFeed();
    }

    private void InitCumulativeDropdowns()
    {
        // 1. Filter Student
        CbFilterStudent.Items.Clear();
        CbFilterStudent.Items.Add("전체 학생");
        foreach (var s in _studentService.Students.OrderBy(s => s.Number))
        {
            CbFilterStudent.Items.Add($"{s.Number}번 {s.Name}");
        }
        CbFilterStudent.SelectedIndex = 0;

        // 2. Filter Category
        CbFilterCategory.Items.Clear();
        CbFilterCategory.Items.Add("전체 영역");
        var categories = new[] { "행동특성", "자율활동", "동아리활동", "봉사활동", "진로활동", "상담일지", "생활지도", "학습태도" };
        foreach (var cat in categories) CbFilterCategory.Items.Add(cat);
        CbFilterCategory.SelectedIndex = 0;

        // 3. New Record Student
        CbRecordStudent.Items.Clear();
        foreach (var s in _studentService.Students.OrderBy(s => s.Number))
        {
            CbRecordStudent.Items.Add($"{s.Number}번 {s.Name}");
        }
        if (CbRecordStudent.Items.Count > 0) CbRecordStudent.SelectedIndex = 0;

        // 4. New Record Category
        CbRecordCategory.Items.Clear();
        foreach (var cat in categories) CbRecordCategory.Items.Add(cat);
        CbRecordCategory.SelectedIndex = 0;

        // 5. New Record Tag
        CbRecordTag.Items.Clear();
        var tags = new[] { "일반", "칭찬/우수", "지도필요", "상담완료" };
        foreach (var tag in tags) CbRecordTag.Items.Add(tag);
        CbRecordTag.SelectedIndex = 0;
    }

    private void RefreshCumulativeFeed()
    {
        var records = _recordService.CumulativeRecords.AsEnumerable();

        if (CbFilterStudent.SelectedIndex > 0 && CbFilterStudent.SelectedItem is string studentStr)
        {
            var parts = studentStr.Split('번');
            if (parts.Length > 0 && int.TryParse(parts[0], out int num))
            {
                records = records.Where(r => r.StudentNumber == num);
            }
        }

        if (CbFilterCategory.SelectedIndex > 0 && CbFilterCategory.SelectedItem is string catStr)
        {
            records = records.Where(r => r.Category == catStr);
        }

        ListCumulativeRecords.ItemsSource = null;
        ListCumulativeRecords.ItemsSource = records.OrderByDescending(r => r.Date).ToList();
    }

    private void CbFilterStudent_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        RefreshCumulativeFeed();
    }

    private void CbFilterCategory_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        RefreshCumulativeFeed();
    }

    private void BtnAddCumulativeRecord_Click(object sender, RoutedEventArgs e)
    {
        string content = TbRecordContent.Text;
        if (string.IsNullOrWhiteSpace(content))
        {
            MessageBox.Show("관찰 내용을 입력해주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        if (CbRecordStudent.SelectedItem is not string studentStr) return;
        var parts = studentStr.Split('번');
        if (parts.Length < 2 || !int.TryParse(parts[0], out int num)) return;
        string name = parts[1].Trim();

        DateTime date = DpRecordDate.SelectedDate ?? DateTime.Today;
        string category = CbRecordCategory.SelectedItem as string ?? "행동특성";
        string tag = CbRecordTag.SelectedItem as string ?? "일반";

        _recordService.AddCumulativeRecord(num, name, date, category, content, tag);

        TbRecordContent.Text = string.Empty;
        RefreshCumulativeFeed();
        HudNotificationWindow.Instance.ShowToast("📝", $"{name} 학생의 누가기록이 등록되었습니다.");
    }

    private void BtnDeleteCumulativeRecord_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string id)
        {
            if (MessageBox.Show("해당 관찰기록을 삭제하시겠습니까?", "확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                _recordService.DeleteCumulativeRecord(id);
                RefreshCumulativeFeed();
            }
        }
    }

    private void BtnCopyNeisSynthesis_Click(object sender, RoutedEventArgs e)
    {
        int studentNum = 1;
        if (CbFilterStudent.SelectedIndex > 0 && CbFilterStudent.SelectedItem is string studentStr)
        {
            var parts = studentStr.Split('번');
            if (parts.Length > 0 && int.TryParse(parts[0], out int num))
            {
                studentNum = num;
            }
        }
        else
        {
            MessageBox.Show("상단에서 나이스 평어를 취합할 특정 학생을 선택해주세요.", "안내", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        string synth = _recordService.GenerateNeisSynthesisText(studentNum);
        Clipboard.SetText(synth);
        HudNotificationWindow.Instance.ShowToast("📋", $"{studentNum}번 학생의 나이스 참고 평어 자료가 클립보드에 복사되었습니다.");
    }

    private void BtnDownloadCumulativeTemplate_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = "누가기록_관찰일지_표준양식.csv",
            Title = "누가기록 표준 양식 다운로드",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                string csv = _recordService.GetCumulativeRecordCsvTemplate();
                _recordService.ExportCsvFile(sfd.FileName, csv);
                HudNotificationWindow.Instance.ShowToast("📄", $"양식이 저장되었습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"양식 저장 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnExportCumulativeCsv_Click(object sender, RoutedEventArgs e)
    {
        var sfd = new SaveFileDialog
        {
            Filter = "CSV 파일 (*.csv)|*.csv",
            FileName = $"누가기록_관찰일지_{DateTime.Now:yyyyMMdd}.csv",
            Title = "누가기록 CSV 내보내기",
            InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
        };
        if (sfd.ShowDialog() == true)
        {
            try
            {
                string csv = _recordService.GetCumulativeRecordCsvTemplate();
                _recordService.ExportCsvFile(sfd.FileName, csv);
                HudNotificationWindow.Instance.ShowToast("💾", $"누가기록이 내보내졌습니다: {Path.GetFileName(sfd.FileName)}");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"내보내기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    #endregion
}
