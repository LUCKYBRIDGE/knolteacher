using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop;

public partial class MainWindow
{
    private static readonly bool V309UxClassHandlersRegistered = RegisterV309UxClassHandlers();
    private static int? _pendingPopupMonitorIndex;

    private PopupLaunchPreferences? _popupLaunchPreferences;
    private bool _v309UxInitialized;

    private static bool RegisterV309UxClassHandlers()
    {
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(MainWindowV309_Loaded),
            handledEventsToo: true);

        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            Mouse.PreviewMouseUpEvent,
            new MouseButtonEventHandler(MainWindowV309_PreviewMouseUp),
            handledEventsToo: true);

        EventManager.RegisterClassHandler(
            typeof(Window),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(PopupWindowV309_Loaded),
            handledEventsToo: true);

        return true;
    }

    private static void MainWindowV309_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is MainWindow window)
        {
            window.InitializeV309Ux();
        }
    }

    private void InitializeV309Ux()
    {
        if (_v309UxInitialized) return;
        _v309UxInitialized = true;

        _popupLaunchPreferences = new PopupLaunchPreferences(_configService.ConfigDir);
        RefreshRuntimeVersionBadge();
        InstallPopupDisplaySettingsMenu();

        if (_updateService is UpdateService updateService &&
            updateService.TryConsumeUpdateCompletion(out string completedVersion))
        {
            HudNotificationWindow.Instance.ShowToast(
                "✅",
                $"놀티쳐 {completedVersion} 업데이트가 완료되었습니다. 새 버전으로 다시 실행되었습니다.");
        }
    }

    private void RefreshRuntimeVersionBadge()
    {
        string runtimeVersion = _updateService.CurrentVersion;
        foreach (var textBlock in FindVisualChildren<TextBlock>(this))
        {
            string text = textBlock.Text ?? string.Empty;
            if (text.StartsWith("🚀 v", StringComparison.Ordinal))
            {
                textBlock.Text = $"🚀 {runtimeVersion}";
            }
        }
    }

    private void InstallPopupDisplaySettingsMenu()
    {
        if (PillMonitorStatus == null) return;

        var menu = PillMonitorStatus.ContextMenu ?? new ContextMenu();
        if (!menu.Items.OfType<MenuItem>().Any(item => Equals(item.Tag, "popup-display-settings")))
        {
            if (menu.Items.Count > 0)
            {
                menu.Items.Add(new Separator());
            }

            var item = new MenuItem
            {
                Header = "🖥️ 팝업 표시 위치 설정...",
                Tag = "popup-display-settings"
            };
            item.Click += (_, _) => OpenPopupDisplaySettings();
            menu.Items.Add(item);
        }

        PillMonitorStatus.ContextMenu = menu;
        string currentTip = PillMonitorStatus.ToolTip?.ToString() ?? "디스플레이 연결 상태";
        if (!currentTip.Contains("팝업 표시 위치", StringComparison.Ordinal))
        {
            PillMonitorStatus.ToolTip = currentTip + "\n우클릭: 팝업 표시 위치 설정";
        }
    }

    private void OpenPopupDisplaySettings()
    {
        _popupLaunchPreferences ??= new PopupLaunchPreferences(_configService.ConfigDir);
        var dialog = new PopupDisplaySettingsDialog(_popupLaunchPreferences, _displayManager)
        {
            Owner = this
        };
        _displayManager.MoveWindowToScreen(dialog, 0, maximize: false);
        dialog.ShowDialog();
    }

    private static void MainWindowV309_PreviewMouseUp(object sender, MouseButtonEventArgs e)
    {
        if (sender is not MainWindow window || e.OriginalSource is not DependencyObject source)
        {
            return;
        }

        FrameworkElement? launcher = FindClickableLauncher(source, window);
        if (launcher == null) return;

        string launcherText = ExtractVisibleText(launcher);
        if (!IsConfirmedPopupLauncher(launcherText)) return;

        window._popupLaunchPreferences ??= new PopupLaunchPreferences(window._configService.ConfigDir);

        if (e.ChangedButton == MouseButton.Right)
        {
            if (!window._popupLaunchPreferences.RightClickOpensOnSecondMonitor)
            {
                return;
            }

            int targetMonitor = window._displayManager.IsDualMonitor ? 1 : 0;
            var visibleBefore = SnapshotVisibleWindows();
            _pendingPopupMonitorIndex = targetMonitor;
            e.Handled = true;

            try
            {
                RaisePrimaryActivation(launcher);
                window.MoveNewPopupWindows(targetMonitor, visibleBefore);
            }
            finally
            {
                _pendingPopupMonitorIndex = null;
            }

            return;
        }

        if (e.ChangedButton == MouseButton.Left)
        {
            var visibleBefore = SnapshotVisibleWindows();
            _pendingPopupMonitorIndex = 0;
            _ = window.Dispatcher.BeginInvoke(
                DispatcherPriority.ContextIdle,
                new Action(() =>
                {
                    try
                    {
                        window.MoveNewPopupWindows(0, visibleBefore);
                    }
                    finally
                    {
                        _pendingPopupMonitorIndex = null;
                    }
                }));
        }
    }

    private static void PopupWindowV309_Loaded(object sender, RoutedEventArgs e)
    {
        if (_pendingPopupMonitorIndex is not int target || sender is not Window popup || popup is MainWindow)
        {
            return;
        }

        MainWindow? main = Application.Current?.Windows.OfType<MainWindow>().FirstOrDefault();
        if (main == null || ReferenceEquals(main, popup)) return;

        main._displayManager.MoveWindowToScreen(popup, target, maximize: false);
    }

    private void MoveNewPopupWindows(int targetMonitor, HashSet<Window> visibleBefore)
    {
        if (Application.Current == null) return;

        foreach (Window candidate in Application.Current.Windows)
        {
            if (candidate is MainWindow || !candidate.IsVisible || visibleBefore.Contains(candidate))
            {
                continue;
            }

            _displayManager.MoveWindowToScreen(candidate, targetMonitor, maximize: false);
        }
    }

    private static HashSet<Window> SnapshotVisibleWindows()
        => Application.Current == null
            ? new HashSet<Window>()
            : Application.Current.Windows.Cast<Window>().Where(w => w.IsVisible).ToHashSet();

    private static FrameworkElement? FindClickableLauncher(DependencyObject source, MainWindow root)
    {
        FrameworkElement? handBorder = null;
        DependencyObject? current = source;

        while (current != null && !ReferenceEquals(current, root))
        {
            if (current is Button button)
            {
                return button;
            }

            if (current is Border border && border.Cursor == Cursors.Hand)
            {
                handBorder ??= border;
            }

            current = VisualTreeHelper.GetParent(current);
        }

        return handBorder;
    }

    private static string ExtractVisibleText(DependencyObject root)
    {
        var builder = new StringBuilder();
        AppendVisibleText(root, builder);
        return builder.ToString();
    }

    private static void AppendVisibleText(DependencyObject current, StringBuilder builder)
    {
        if (current is TextBlock tb && !string.IsNullOrWhiteSpace(tb.Text))
        {
            builder.Append(' ').Append(tb.Text.Trim());
        }
        else if (current is ContentControl cc && cc.Content is string content && !string.IsNullOrWhiteSpace(content))
        {
            builder.Append(' ').Append(content.Trim());
        }

        int count = VisualTreeHelper.GetChildrenCount(current);
        for (int i = 0; i < count; i++)
        {
            AppendVisibleText(VisualTreeHelper.GetChild(current, i), builder);
        }
    }

    private static bool IsConfirmedPopupLauncher(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return false;

        // NolBoard, its internal widgets, screen overlays and floating docks are workspaces/tools,
        // not ordinary popup windows. Keep them out of the right-click monitor gesture.
        if (text.Contains("놀보드", StringComparison.Ordinal) ||
            text.Contains("위젯", StringComparison.Ordinal) ||
            text.Contains("화면판서", StringComparison.Ordinal) ||
            text.Contains("칠판보드", StringComparison.Ordinal) ||
            text.Contains("플로팅", StringComparison.Ordinal))
        {
            return false;
        }

        string[] popupSignals =
        {
            "타이머",
            "추첨",
            "실물화상기",
            "스마트 자리 바꾸기",
            "교실 소음 신호등",
            "QR코드",
            "학급 관리 허브",
            "사운드보드",
            "복무 계산기",
            "전자 서명",
            "전국 학교 지도",
            "양식 다운로드",
            "저장폴더",
            "버전확인",
            "일정 등록",
            "알림장 크게 보기",
            "D-Day"
        };

        return popupSignals.Any(signal => text.Contains(signal, StringComparison.Ordinal));
    }

    private static void RaisePrimaryActivation(FrameworkElement launcher)
    {
        if (launcher is Button button)
        {
            button.RaiseEvent(new RoutedEventArgs(Button.ClickEvent, button));
            return;
        }

        if (launcher is Border border)
        {
            var args = new MouseButtonEventArgs(Mouse.PrimaryDevice, Environment.TickCount, MouseButton.Left)
            {
                RoutedEvent = Mouse.MouseUpEvent,
                Source = border
            };
            border.RaiseEvent(args);
        }
    }

    private static IEnumerable<T> FindVisualChildren<T>(DependencyObject root) where T : DependencyObject
    {
        if (root == null) yield break;

        int count = VisualTreeHelper.GetChildrenCount(root);
        for (int i = 0; i < count; i++)
        {
            DependencyObject child = VisualTreeHelper.GetChild(root, i);
            if (child is T typed)
            {
                yield return typed;
            }

            foreach (T descendant in FindVisualChildren<T>(child))
            {
                yield return descendant;
            }
        }
    }
}
