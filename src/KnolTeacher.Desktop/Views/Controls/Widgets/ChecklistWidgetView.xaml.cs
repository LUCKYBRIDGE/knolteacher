using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class ChecklistWidgetView : UserControl
{
    private readonly IConfigService _configService;
    private readonly IStudentManagerService? _studentService;
    private ChecklistTabItem? _currentTab;

    public ChecklistWidgetView(IConfigService configService, IStudentManagerService? studentService = null)
    {
        InitializeComponent();
        _configService = configService;
        _studentService = studentService;

        Loaded += (s, e) => InitializeData();
    }

    public void InitializeData()
    {
        var store = _configService.ChecklistStore;
        if (store.Tabs.Count == 0)
        {
            // Create default tabs
            var defaultTab = CreateNewTabItem("과제 검사");
            store.Tabs.Add(defaultTab);
            store.ActiveTabId = defaultTab.Id;
            _configService.SaveChecklistStore();
        }

        _currentTab = store.Tabs.FirstOrDefault(t => t.Id == store.ActiveTabId) ?? store.Tabs.First();
        BtnToggleNameMode.Content = store.ShowStudentNames ? "이름" : "번호";

        RenderTabs();
        RenderStudents();
    }

    private ChecklistTabItem CreateNewTabItem(string title)
    {
        var tab = new ChecklistTabItem { Title = title };
        int studentCount = 25;
        if (_studentService != null && _studentService.Students.Count > 0)
        {
            studentCount = _studentService.Students.Count;
            for (int i = 0; i < studentCount; i++)
            {
                var st = _studentService.Students[i];
                tab.Students.Add(new ChecklistStudentItem
                {
                    Number = st.Number,
                    Name = st.Name,
                    IsChecked = false
                });
            }
        }
        else
        {
            for (int i = 1; i <= studentCount; i++)
            {
                tab.Students.Add(new ChecklistStudentItem
                {
                    Number = i,
                    Name = $"{i}번",
                    IsChecked = false
                });
            }
        }
        return tab;
    }

    private void RenderTabs()
    {
        PanelTabs.Children.Clear();
        var store = _configService.ChecklistStore;

        foreach (var tab in store.Tabs)
        {
            bool isActive = _currentTab != null && _currentTab.Id == tab.Id;
            var btn = new Button
            {
                Content = tab.Title,
                Height = 24,
                Padding = new Thickness(8, 0, 8, 0),
                Margin = new Thickness(0, 0, 4, 0),
                FontSize = 11,
                FontWeight = isActive ? FontWeights.Bold : FontWeights.Normal,
                Background = isActive ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7")) : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                Foreground = isActive ? Brushes.White : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8")),
                BorderThickness = new Thickness(0),
                Cursor = System.Windows.Input.Cursors.Hand,
                Tag = tab.Id
            };

            var borderStyle = new Style(typeof(Border));
            borderStyle.Setters.Add(new Setter(Border.CornerRadiusProperty, new CornerRadius(4)));
            btn.Resources.Add(typeof(Border), borderStyle);

            btn.Click += (s, e) =>
            {
                _currentTab = tab;
                store.ActiveTabId = tab.Id;
                _configService.SaveChecklistStore();
                RenderTabs();
                RenderStudents();
            };

            PanelTabs.Children.Add(btn);
        }
    }

    private void RenderStudents()
    {
        PanelStudentGrid.Children.Clear();
        if (_currentTab == null) return;

        bool showNames = _configService.ChecklistStore.ShowStudentNames;
        int checkedCount = 0;

        foreach (var student in _currentTab.Students)
        {
            if (student.IsChecked) checkedCount++;

            string label = showNames && !string.IsNullOrWhiteSpace(student.Name)
                ? (student.Name.Length > 3 ? student.Name.Substring(0, 3) : student.Name)
                : $"{student.Number}";

            var btn = new Button
            {
                Width = 52,
                Height = 36,
                Margin = new Thickness(3),
                Cursor = System.Windows.Input.Cursors.Hand,
                BorderThickness = new Thickness(1),
                Tag = student
            };

            var borderStyle = new Style(typeof(Border));
            borderStyle.Setters.Add(new Setter(Border.CornerRadiusProperty, new CornerRadius(6)));
            btn.Resources.Add(typeof(Border), borderStyle);

            if (student.IsChecked)
            {
                btn.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
                btn.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#34D399"));
                btn.Foreground = Brushes.White;
                btn.Content = new StackPanel
                {
                    Orientation = Orientation.Horizontal,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    Children =
                    {
                        new TextBlock { Text = "✓ ", FontSize = 10, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center },
                        new TextBlock { Text = label, FontSize = 11, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center }
                    }
                };
            }
            else
            {
                btn.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B"));
                btn.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155"));
                btn.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CBD5E1"));
                btn.Content = new TextBlock
                {
                    Text = label,
                    FontSize = 11,
                    FontWeight = FontWeights.SemiBold,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center
                };
            }

            btn.Click += (s, e) =>
            {
                student.IsChecked = !student.IsChecked;
                student.CheckedAt = student.IsChecked ? DateTime.Now : null;
                _configService.SaveChecklistStore();
                RenderStudents();
            };

            PanelStudentGrid.Children.Add(btn);
        }

        int totalCount = _currentTab.Students.Count;
        int pendingCount = totalCount - checkedCount;

        TxtPendingBadge.Text = $"미완료 {pendingCount}명";
        TxtTotalRatio.Text = $"완료 {checkedCount}/{totalCount}명";

        BorderPendingBadge.Background = pendingCount == 0
            ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"))
            : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DC2626"));
    }

    private void BtnAddTab_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new Window
        {
            Title = "새 체크리스트 탭 추가",
            Width = 340,
            Height = 180,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0F172A")),
            ResizeMode = ResizeMode.NoResize
        };

        var sp = new StackPanel { Margin = new Thickness(16) };
        sp.Children.Add(new TextBlock { Text = "체크리스트 이름 (예: 준비물, 일기장)", Foreground = Brushes.White, FontSize = 12, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 0, 8) });
        var tb = new TextBox { Text = "새 과제", Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")), Foreground = Brushes.White, Height = 32, Padding = new Thickness(6), BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")), Margin = new Thickness(0, 0, 0, 14) };
        sp.Children.Add(tb);

        var btnPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var btnOk = new Button { Content = "추가", Width = 70, Height = 30, Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7")), Foreground = Brushes.White, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 0, 8, 0) };
        var btnCancel = new Button { Content = "취소", Width = 60, Height = 30, Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")), Foreground = Brushes.White };

        btnOk.Click += (s2, e2) =>
        {
            string title = tb.Text.Trim();
            if (!string.IsNullOrWhiteSpace(title))
            {
                var newTab = CreateNewTabItem(title);
                _configService.ChecklistStore.Tabs.Add(newTab);
                _configService.ChecklistStore.ActiveTabId = newTab.Id;
                _currentTab = newTab;
                _configService.SaveChecklistStore();
                RenderTabs();
                RenderStudents();
                dialog.Close();
            }
        };
        btnCancel.Click += (s2, e2) => dialog.Close();

        btnPanel.Children.Add(btnOk);
        btnPanel.Children.Add(btnCancel);
        sp.Children.Add(btnPanel);
        dialog.Content = sp;
        dialog.ShowDialog();
    }

    private void BtnDeleteCurrentTab_Click(object sender, RoutedEventArgs e)
    {
        if (_currentTab == null) return;
        var store = _configService.ChecklistStore;
        if (store.Tabs.Count <= 1)
        {
            MessageBox.Show("최소 1개의 체크리스트 탭은 유지되어야 합니다.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        if (MessageBox.Show($"'{_currentTab.Title}' 탭을 삭제하시겠습니까?", "탭 삭제 확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            store.Tabs.Remove(_currentTab);
            _currentTab = store.Tabs.First();
            store.ActiveTabId = _currentTab.Id;
            _configService.SaveChecklistStore();
            RenderTabs();
            RenderStudents();
        }
    }

    private void BtnCheckAll_Click(object sender, RoutedEventArgs e)
    {
        if (_currentTab == null) return;
        foreach (var st in _currentTab.Students)
        {
            st.IsChecked = true;
            st.CheckedAt = DateTime.Now;
        }
        _configService.SaveChecklistStore();
        RenderStudents();
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        if (_currentTab == null) return;
        if (MessageBox.Show("현재 탭의 모든 체크 상태를 초기화하시겠습니까?", "초기화 확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            foreach (var st in _currentTab.Students)
            {
                st.IsChecked = false;
                st.CheckedAt = null;
            }
            _configService.SaveChecklistStore();
            RenderStudents();
        }
    }

    private void BtnToggleNameMode_Click(object sender, RoutedEventArgs e)
    {
        var store = _configService.ChecklistStore;
        store.ShowStudentNames = !store.ShowStudentNames;
        BtnToggleNameMode.Content = store.ShowStudentNames ? "이름" : "번호";
        _configService.SaveChecklistStore();
        RenderStudents();
    }
}
