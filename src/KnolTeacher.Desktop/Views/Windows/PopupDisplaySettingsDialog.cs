using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public sealed class PopupDisplaySettingsDialog : Window
{
    private readonly PopupLaunchPreferences _preferences;
    private readonly CheckBox _rightClickSecondMonitor;

    public PopupDisplaySettingsDialog(PopupLaunchPreferences preferences, IDisplayManager displayManager)
    {
        _preferences = preferences;

        Title = "팝업 표시 설정";
        Width = 470;
        Height = 300;
        MinWidth = 430;
        MinHeight = 280;
        ResizeMode = ResizeMode.NoResize;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = new SolidColorBrush(Color.FromRgb(248, 250, 252));

        var root = new Grid { Margin = new Thickness(22) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var header = new StackPanel { Margin = new Thickness(0, 0, 0, 16) };
        header.Children.Add(new TextBlock
        {
            Text = "🖥️ 팝업 표시 위치",
            FontSize = 18,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush(Color.FromRgb(15, 23, 42))
        });
        header.Children.Add(new TextBlock
        {
            Text = "독립 창·대화상자로 확실히 열리는 기능에만 적용됩니다.",
            FontSize = 11.5,
            Margin = new Thickness(0, 5, 0, 0),
            Foreground = new SolidColorBrush(Color.FromRgb(100, 116, 139))
        });
        Grid.SetRow(header, 0);
        root.Children.Add(header);

        var body = new Border
        {
            Background = Brushes.White,
            BorderBrush = new SolidColorBrush(Color.FromRgb(226, 232, 240)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(10),
            Padding = new Thickness(16)
        };
        var bodyStack = new StackPanel();
        _rightClickSecondMonitor = new CheckBox
        {
            Content = "우클릭한 팝업을 모니터 2에 열기",
            IsChecked = _preferences.RightClickOpensOnSecondMonitor,
            FontSize = 13,
            FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(Color.FromRgb(30, 41, 59)),
            Cursor = System.Windows.Input.Cursors.Hand
        };
        bodyStack.Children.Add(_rightClickSecondMonitor);
        bodyStack.Children.Add(new TextBlock
        {
            Text = "• 왼클릭: 모니터 1(교사용 화면)\n• 우클릭: 모니터 2(학생용 화면)\n• 놀보드 내부 위젯·탭·드로어에는 적용하지 않음",
            TextWrapping = TextWrapping.Wrap,
            FontSize = 11.5,
            LineHeight = 18,
            Margin = new Thickness(24, 10, 0, 0),
            Foreground = new SolidColorBrush(Color.FromRgb(71, 85, 105))
        });

        string monitorText = displayManager.IsDualMonitor
            ? $"현재 {displayManager.ScreenCount}대의 모니터가 감지되었습니다."
            : "현재는 단일 모니터입니다. 모니터 2가 없으면 자동으로 모니터 1을 사용합니다.";
        bodyStack.Children.Add(new TextBlock
        {
            Text = monitorText,
            FontSize = 10.5,
            Margin = new Thickness(0, 13, 0, 0),
            Foreground = new SolidColorBrush(Color.FromRgb(100, 116, 139))
        });
        body.Child = bodyStack;
        Grid.SetRow(body, 1);
        root.Children.Add(body);

        var actions = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(0, 16, 0, 0)
        };
        var cancel = new Button { Content = "취소", Width = 78, Height = 34, Margin = new Thickness(0, 0, 8, 0) };
        cancel.Click += (_, _) => { DialogResult = false; Close(); };
        var save = new Button
        {
            Content = "저장",
            Width = 92,
            Height = 34,
            FontWeight = FontWeights.Bold,
            Background = new SolidColorBrush(Color.FromRgb(37, 99, 235)),
            Foreground = Brushes.White,
            BorderThickness = new Thickness(0)
        };
        save.Click += (_, _) =>
        {
            _preferences.RightClickOpensOnSecondMonitor = _rightClickSecondMonitor.IsChecked == true;
            _preferences.Save();
            DialogResult = true;
            Close();
        };
        actions.Children.Add(cancel);
        actions.Children.Add(save);
        Grid.SetRow(actions, 2);
        root.Children.Add(actions);

        Content = root;
    }
}
