using System;
using System.Threading;
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Wpf.Ui.Appearance;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.ViewModels;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop;

public partial class App : Application
{
    private static Mutex? _mutex;
    private const string MutexName = "KnolTeacherDesktopNetMutex";

    private readonly IHost _host;

    public App()
    {
        // Global Unhandled Exception Handling
        DispatcherUnhandledException += (s, args) =>
        {
            BootLog($"[DispatcherUnhandledException] {args.Exception}");
            MessageBox.Show($"UI 예외 발생:\n{args.Exception.Message}\n\n{args.Exception.StackTrace}",
                "놀티쳐 .NET 오류", MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };

        AppDomain.CurrentDomain.UnhandledException += (s, args) =>
        {
            if (args.ExceptionObject is Exception ex)
            {
                BootLog($"[AppDomain UnhandledException] {ex}");
                MessageBox.Show($"시스템 예외 발생:\n{ex.Message}\n\n{ex.StackTrace}",
                    "놀티쳐 .NET 치명적 오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        };

        _host = Host.CreateDefaultBuilder()
            .ConfigureServices((context, services) =>
            {
                // Core Services
                services.AddSingleton<IConfigService, ConfigService>();
                services.AddSingleton<IThemeService, ThemeService>();
                services.AddSingleton<IDisplayManager, DisplayManager>();
                services.AddSingleton<IGlobalHotkeyService, GlobalHotkeyService>();
                services.AddSingleton<IDesktopCleanerService, DesktopCleanerService>();
                services.AddSingleton<IStudentManagerService, StudentManagerService>();
                services.AddSingleton<INeisService, NeisService>();
                services.AddSingleton<ISoundService, SoundService>();
                services.AddSingleton<ITimetableService, TimetableService>();
                services.AddSingleton<ISchedulerService, SchedulerService>();
                services.AddSingleton<IYouTubeService, YouTubeService>();
                services.AddSingleton<ISiteBookmarkService, SiteBookmarkService>();

                // ViewModels
                services.AddSingleton<MainViewModel>();

                // Windows
                services.AddSingleton<MainWindow>();
                services.AddSingleton<StudentDisplayWindow>();
                services.AddSingleton<ScreenDrawingOverlayWindow>();
                services.AddSingleton<VisualizerWindow>();
                services.AddSingleton<ClassroomTimerWindow>();
                services.AddSingleton<StudentPickerWindow>();
                services.AddSingleton<FloatingToolbarWindow>();
                services.AddSingleton<YouTubePlayerWindow>();
            })
            .Build();
    }

    public static void BootLog(string msg)
    {
        try
        {
            var logPath = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "knol_boot.log");
            System.IO.File.AppendAllText(logPath, $"[{DateTime.Now:HH:mm:ss.fff}] {msg}\r\n");
        }
        catch { }
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        BootLog("OnStartup started");
        try
        {
            // 1. Single-Instance Check
            _mutex = new Mutex(true, MutexName, out bool createdNew);
            BootLog($"Mutex createdNew: {createdNew}");
            if (!createdNew)
            {
                BootLog("Single instance check failed, shutting down");
                MessageBox.Show("놀티쳐가 이미 실행 중입니다.", "놀티쳐 .NET", MessageBoxButton.OK, MessageBoxImage.Information);
                Shutdown();
                return;
            }

            base.OnStartup(e);
            BootLog("base.OnStartup done");

            // 2. Start DI Host
            _host.Start();
            BootLog("DI host started");

            // 3. Apply Theme
            try
            {
                var themeService = _host.Services.GetRequiredService<IThemeService>();
                themeService.ApplyTheme(themeService.CurrentTheme);
                BootLog($"Theme applied: {themeService.CurrentTheme}");
            }
            catch (Exception ex)
            {
                BootLog($"Theme error: {ex}");
            }

            // 4. Show MainWindow First
            BootLog("Resolving MainWindow...");
            var mainWindow = _host.Services.GetRequiredService<MainWindow>();
            MainWindow = mainWindow;
            ShutdownMode = ShutdownMode.OnMainWindowClose;
            BootLog("Showing MainWindow...");
            mainWindow.Show();
            mainWindow.Activate();
            BootLog("MainWindow shown successfully");

            // 5. Initialize Global Hotkeys & Tool Handlers
            BootLog("Starting step 5: hotkeys...");
            try
            {
                var hotkeyService = _host.Services.GetRequiredService<IGlobalHotkeyService>();
                BootLog("Calling hotkeyService.Initialize()...");
                hotkeyService.Initialize();
                BootLog("hotkeyService.Initialize() done");
                var displayManager = _host.Services.GetRequiredService<IDisplayManager>();
                BootLog("displayManager resolved");

                hotkeyService.HotkeyPressed += (action) =>
                {
                    Dispatcher.Invoke(() =>
                    {
                        switch (action)
                        {
                            case "board":
                            case "board_f2":
                                var studentBoard = _host.Services.GetRequiredService<StudentDisplayWindow>();
                                if (studentBoard.IsVisible)
                                {
                                    studentBoard.Hide();
                                    HudNotificationWindow.Instance.ShowToast("📺", "놀티쳐 보드 닫힘");
                                }
                                else
                                {
                                    if (displayManager.ScreenCount > 1)
                                    {
                                        displayManager.MoveWindowToScreen(studentBoard, 1, maximize: true);
                                    }
                                    studentBoard.Show();
                                    studentBoard.Activate();
                                    HudNotificationWindow.Instance.ShowToast("📺", "놀티쳐 보드 열림 (F2)");
                                }
                                break;

                            case "drawing":
                                var screenDrawing = _host.Services.GetRequiredService<ScreenDrawingOverlayWindow>();
                                if (screenDrawing.IsVisible)
                                {
                                    screenDrawing.CloseOverlay();
                                    HudNotificationWindow.Instance.ShowToast("✏️", "화면 판서 종료 (ESC)");
                                }
                                else
                                {
                                    screenDrawing.FreezeAndShow();
                                    HudNotificationWindow.Instance.ShowToast("✏️", "화면 전체 판서 시작 (Alt+2)");
                                }
                                break;

                            case "timer":
                                var timerWindow = _host.Services.GetRequiredService<ClassroomTimerWindow>();
                                if (timerWindow.IsVisible)
                                {
                                    timerWindow.Hide();
                                    HudNotificationWindow.Instance.ShowToast("⏱️", "교실 타이머 숨김");
                                }
                                else
                                {
                                    timerWindow.Show();
                                    timerWindow.Activate();
                                    HudNotificationWindow.Instance.ShowToast("⏱️", "교실 집중 타이머 (Alt+3)");
                                }
                                break;

                            case "picker":
                                var pickerWindow = _host.Services.GetRequiredService<StudentPickerWindow>();
                                if (pickerWindow.IsVisible)
                                {
                                    pickerWindow.Hide();
                                    HudNotificationWindow.Instance.ShowToast("🎲", "발표자 추첨 숨김");
                                }
                                else
                                {
                                    pickerWindow.Show();
                                    pickerWindow.Activate();
                                    HudNotificationWindow.Instance.ShowToast("🎲", "발표자 추첨기 (Alt+8)");
                                }
                                break;

                            case "dock":
                                var dockWindow = _host.Services.GetRequiredService<FloatingToolbarWindow>();
                                if (dockWindow.IsVisible)
                                {
                                    dockWindow.Hide();
                                    HudNotificationWindow.Instance.ShowToast("🏝️", "스마트 독 숨김");
                                }
                                else
                                {
                                    dockWindow.Show();
                                    dockWindow.Activate();
                                    HudNotificationWindow.Instance.ShowToast("🏝️", "스마트 독 열림 (Alt+9)");
                                }
                                break;

                            case "visualizer":
                                var visualizer = _host.Services.GetRequiredService<VisualizerWindow>();
                                visualizer.Show();
                                visualizer.Activate();
                                HudNotificationWindow.Instance.ShowToast("📷", "스마트 실물화상기");
                                break;

                            case "youtube":
                                var youtubePlayer = _host.Services.GetRequiredService<YouTubePlayerWindow>();
                                if (youtubePlayer.IsVisible)
                                {
                                    youtubePlayer.Hide();
                                    HudNotificationWindow.Instance.ShowToast("🎵", "유튜브 플레이어 숨김");
                                }
                                else
                                {
                                    youtubePlayer.Show();
                                    youtubePlayer.Activate();
                                    HudNotificationWindow.Instance.ShowToast("🎵", "무광고 유튜브 BGM 플레이어");
                                }
                                break;
                        }
                    });
                };
                BootLog("Step 5 completed successfully");
            }
            catch (Exception ex)
            {
                BootLog($"Hotkey/tool init error: {ex}");
                var fullErr = ex.InnerException != null ? $"{ex.Message}\n\n[상세 정보]: {ex.InnerException.Message}" : ex.Message;
                MessageBox.Show($"핫키 초기화 알림: {fullErr}", "안내", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
            // 6. Start Background Scheduler Service
            try
            {
                var scheduler = _host.Services.GetRequiredService<ISchedulerService>();
                scheduler.Start();
                BootLog("Scheduler service started successfully");
            }
            catch (Exception ex)
            {
                BootLog($"Scheduler service start note: {ex.Message}");
            }

            BootLog("OnStartup finished completely");
        }
        catch (Exception ex)
        {
            BootLog($"FATAL OnStartup error: {ex}");
            MessageBox.Show($"시작 오류 발생:\n{ex.Message}\n\n{ex.StackTrace}", "시작 오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        BootLog($"OnExit called with Application ExitCode: {e.ApplicationExitCode}");
        try
        {
            var hotkeyService = _host.Services.GetService<IGlobalHotkeyService>();
            hotkeyService?.Dispose();

            await _host.StopAsync();
            _host.Dispose();

            _mutex?.ReleaseMutex();
            _mutex?.Dispose();
        }
        catch { }

        base.OnExit(e);
    }
}
