using System;
using System.Drawing;
using System.IO;
using System.Windows;
using System.Windows.Forms;
using Application = System.Windows.Application;

namespace KnolTeacher.Desktop.Services;

public interface ITrayService : IDisposable
{
    void Initialize(Window mainWindow, Action? openMapAction = null, Action? openSignatureAction = null);
    void ShowBalloon(string title, string message, ToolTipIcon icon = ToolTipIcon.Info);
}

public class TrayService : ITrayService
{
    private NotifyIcon? _notifyIcon;
    private Window? _mainWindow;
    private bool _isExplicitExit = false;
    private bool _hasShownFirstMinimizeNotice = false;

    public void Initialize(Window mainWindow, Action? openMapAction = null, Action? openSignatureAction = null)
    {
        if (_notifyIcon != null) return;
        _mainWindow = mainWindow;

        Icon icon;
        try
        {
            string iconPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "assets", "app_icon.ico");
            if (File.Exists(iconPath))
            {
                icon = new Icon(iconPath);
            }
            else
            {
                icon = SystemIcons.Application;
            }
        }
        catch
        {
            icon = SystemIcons.Application;
        }

        var menu = new ContextMenuStrip();

        // 1. Open / Toggle KnolTeacher
        var itemOpen = new ToolStripMenuItem("🏫 놀티쳐 열기 / 숨기기", null, (s, e) => ToggleMainWindow())
        {
            Font = new Font(menu.Font, System.Drawing.FontStyle.Bold)
        };
        menu.Items.Add(itemOpen);
        menu.Items.Add(new ToolStripSeparator());

        // 2. Direct tool shortcuts
        menu.Items.Add(new ToolStripMenuItem("🎰 스마트 핀볼 추첨기 (Alt+8)", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var pickerWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.StudentPickerWindow)) as Views.Windows.StudentPickerWindow;
                pickerWin?.Show();
                pickerWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("⏱️ 교실 집중 타이머 (Alt+3)", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var timerWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.ClassroomTimerWindow)) as Views.Windows.ClassroomTimerWindow;
                timerWin?.Show();
                timerWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("🚦 교실 소음 신호등 (Alt+N)", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var noiseWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.NoiseTrafficLightWindow)) as Views.Windows.NoiseTrafficLightWindow;
                noiseWin?.Show();
                noiseWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("🔔 교실 효과음 사운드보드 (Alt+B)", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var soundWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.ClassroomSoundboardWindow)) as Views.Windows.ClassroomSoundboardWindow;
                soundWin?.Show();
                soundWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("🔏 전자서명 & 도장 생성기 (Alt+S)", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() => openSignatureAction?.Invoke());
        }));

        menu.Items.Add(new ToolStripMenuItem("🪑 스마트 자리 바꾸기", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var seatWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.SmartSeatShuffleWindow)) as Views.Windows.SmartSeatShuffleWindow;
                seatWin?.Show();
                seatWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("🧮 월 15일 복무 계산기", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                var workWin = (Application.Current as App)?.Services?.GetService(typeof(Views.Windows.WorkdayCalculatorWindow)) as Views.Windows.WorkdayCalculatorWindow;
                workWin?.Show();
                workWin?.Activate();
            });
        }));

        menu.Items.Add(new ToolStripMenuItem("🗺️ 전국 학교 통계 지도", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() => openMapAction?.Invoke());
        }));

        menu.Items.Add(new ToolStripSeparator());

        // 3. Hotkey cheat-sheet
        menu.Items.Add(new ToolStripMenuItem("⌨️ 전역 단축키 가이드", null, (s, e) =>
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                System.Windows.MessageBox.Show(
                    "⚡ 놀티쳐 전역 단축키 안내\n\n" +
                    "놀티쳐 창을 띄워놓지 않아도 언제 어디서든 즉시 동작합니다:\n\n" +
                    "• [Alt + 1] 또는 [F2] : 📺 학생용 놀보드 (전자칠판 전송)\n" +
                    "• [Alt + 2] : ✏️ 화면 판서 그리기 오버레이\n" +
                    "• [Alt + 3] : ⏱️ 교실 집중 타이머 (원형/숫자)\n" +
                    "• [Alt + 4] 또는 [Alt + 8] : 🎲 발표자 추첨기\n" +
                    "• [Alt + 5] : 🚦 교실 소음 신호등\n" +
                    "• [Alt + 6] : 🔔 교실 원터치 효과음 보드\n" +
                    "• [Alt + 9] : 🏝️ 화면 상단 도구바\n" +
                    "• [Alt + S] : 🔏 전자서명 및 도장 생성기\n\n" +
                    "창을 닫아도 시스템 트레이에 상주하므로 수업 중 언제든 편리하게 활용하세요!",
                    "놀티쳐 전역 단축키 가이드",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            });
        }));

        // 4. Exit Application
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add(new ToolStripMenuItem("❌ 놀티쳐 완전 종료", null, (s, e) => ExitApplication()));

        _notifyIcon = new NotifyIcon
        {
            Icon = icon,
            Text = "놀티쳐 (KnolTeacher) - 교실 올인원 도구",
            Visible = true,
            ContextMenuStrip = menu
        };

        _notifyIcon.DoubleClick += (s, e) => ToggleMainWindow();

        // Intercept MainWindow closing
        _mainWindow.Closing += MainWindow_Closing;
    }

    private void MainWindow_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (!_isExplicitExit)
        {
            e.Cancel = true;
            _mainWindow?.Hide();

            if (!_hasShownFirstMinimizeNotice)
            {
                _hasShownFirstMinimizeNotice = true;
                ShowBalloon("놀티쳐가 트레이에 상주합니다", "창을 띄워놓지 않아도 Alt+1~9 단축키는 언제나 즉시 동작합니다!\n작업표시줄 트레이 아이콘을 더블클릭하면 다시 열립니다.");
            }
        }
    }

    public void ShowBalloon(string title, string message, ToolTipIcon icon = ToolTipIcon.Info)
    {
        _notifyIcon?.ShowBalloonTip(3000, title, message, icon);
    }

    private void ToggleMainWindow()
    {
        if (_mainWindow == null) return;

        Application.Current.Dispatcher.Invoke(() =>
        {
            if (_mainWindow.IsVisible)
            {
                if (_mainWindow.WindowState == WindowState.Minimized)
                {
                    _mainWindow.WindowState = WindowState.Normal;
                    _mainWindow.Activate();
                }
                else
                {
                    _mainWindow.Hide();
                }
            }
            else
            {
                _mainWindow.Show();
                _mainWindow.WindowState = WindowState.Normal;
                _mainWindow.Activate();
            }
        });
    }

    private void ExitApplication()
    {
        _isExplicitExit = true;
        _notifyIcon?.Dispose();
        _notifyIcon = null;

        Application.Current.Dispatcher.Invoke(() =>
        {
            _mainWindow?.Close();
            Application.Current.Shutdown();
        });
    }

    public void Dispose()
    {
        _isExplicitExit = true;
        _notifyIcon?.Dispose();
        _notifyIcon = null;
    }
}
