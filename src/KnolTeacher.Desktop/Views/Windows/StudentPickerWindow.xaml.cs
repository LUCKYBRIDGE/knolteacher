using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentPickerWindow : Window
{
    private readonly IStudentManagerService _studentService;
    private readonly ISoundService _soundService;
    private readonly IDisplayManager? _displayManager;
    private int _currentMonitorIndex = 1;

    // Simulation State
    private readonly List<RaceRacer> _racers = new();
    private readonly List<RaceBumper> _bumpers = new();
    private readonly List<RaceRail> _rails = new();
    private readonly List<RotatingLog> _rotatingLogs = new();

    private DispatcherTimer? _gameTimer;
    private bool _isPlaying = false;
    private bool _soundEnabled = true;
    private double _speedMultiplier = 1.0;
    private DateTime _lastFrameTime = DateTime.UtcNow;

    private const double TrackWidth = 680.0;
    private const double TrackHeight = 2200.0;
    private const double FinishY = 2050.0;

    private int _targetWinnerCount = 1;
    private int _finishedCount = 0;
    private readonly List<StudentItem> _winners = new();

    public StudentPickerWindow(IStudentManagerService studentService, ISoundService soundService, IDisplayManager? displayManager = null)
    {
        _studentService = studentService;
        _soundService = soundService;
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        InitializeComponent();

        Loaded += (s, e) =>
        {
            SetupCourseScenery();
            ResetToStartLine();
            PositionToDefaultMonitor();
            UpdateCameraViewport(0, force: true);
        };

        KeyDown += Window_KeyDown;
    }

    public void PositionToDefaultMonitor()
    {
        if (_displayManager != null)
        {
            _currentMonitorIndex = _displayManager.RecommendedStudentMonitorIndex;
            _displayManager.MoveToStudentMonitor(this, maximize: false);
            UpdateMonitorButtonText();
        }
    }

    private void UpdateMonitorButtonText()
    {
        if (BtnSwitchMonitor != null)
        {
            BtnSwitchMonitor.Content = _currentMonitorIndex == 1 ? "📺 모니터 2" : "💻 모니터 1";
        }
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        if (_displayManager == null || _displayManager.ScreenCount < 2) return;
        _currentMonitorIndex = _currentMonitorIndex == 1 ? 0 : 1;
        _displayManager.MoveWindowToScreen(this, _currentMonitorIndex, maximize: false);
        UpdateMonitorButtonText();
    }

    private void Window_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Space)
        {
            if (GridCelebration.Visibility == Visibility.Visible)
            {
                DismissCelebration();
            }
            else if (!_isPlaying)
            {
                StartRaceSimulation();
            }
            e.Handled = true;
        }
        else if (e.Key == Key.Escape)
        {
            if (GridCelebration.Visibility == Visibility.Visible)
            {
                DismissCelebration();
            }
            else
            {
                Hide();
            }
            e.Handled = true;
        }
    }

    #region Course Scenery & Obstacles Setup

    private void SetupCourseScenery()
    {
        foreach (var b in _bumpers) RaceCanvas.Children.Remove(b.Visual);
        foreach (var l in _rotatingLogs) RaceCanvas.Children.Remove(l.Visual);
        _bumpers.Clear();
        _rails.Clear();
        _rotatingLogs.Clear();

        // 1. Zone 2 Slanted Cartoon Wood Rails (Collision definition)
        _rails.Add(new RaceRail(80, 310, 270, 410, 18));
        _rails.Add(new RaceRail(600, 310, 410, 410, 18));

        // 2. Zone 3 Mid-track Cartoon Wood Rails
        _rails.Add(new RaceRail(50, 1110, 250, 1190, 18));
        _rails.Add(new RaceRail(630, 1110, 430, 1190, 18));

        // 3. Zone 5 Waterfall Funnel Banks
        _rails.Add(new RaceRail(0, 1880, 230, 2030, 20));
        _rails.Add(new RaceRail(680, 1880, 450, 2030, 20));
        _rails.Add(new RaceRail(230, 2030, 230, 2200, 20));
        _rails.Add(new RaceRail(450, 2030, 450, 2200, 20));

        // 4. ROTATING LOGS (회전 통나무 동적 장애물!)
        // Upper Slope: Clockwise Rotating Log in center
        AddRotatingLog(340, 520, 220, 34, 2.2, 15);

        // Mid-Course Twin Shuffling Logs: counter-rotating to create exciting pinball channels!
        AddRotatingLog(220, 880, 180, 32, -2.5, -30);
        AddRotatingLog(460, 880, 180, 32, 2.5, 30);

        // Lower Mushroom Forest: Slower Heavy Rotating Log
        AddRotatingLog(340, 1460, 210, 36, -1.8, 0);

        // 5. CARTOON BUMPERS (통통 튀는 만화풍 버섯 & 별)
        // Zone 2 Upper side bumpers
        AddBumper(150, 640, 32, "cartoon_mushroom_yellow.png");
        AddBumper(530, 640, 32, "cartoon_mushroom_yellow.png");

        // Zone 3 Star Bouncer in center
        AddBumper(340, 1060, 36, "cartoon_star_bumper.png");

        // Zone 4 Enchanted Mushroom Forest
        AddBumper(190, 1320, 34, "cartoon_mushroom_red.png");
        AddBumper(490, 1320, 34, "cartoon_mushroom_red.png");
        AddBumper(160, 1600, 34, "cartoon_mushroom_purple.png");
        AddBumper(520, 1600, 34, "cartoon_mushroom_purple.png");
        AddBumper(260, 1720, 34, "cartoon_mushroom_red.png");
        AddBumper(420, 1720, 34, "cartoon_mushroom_red.png");
        AddBumper(340, 1830, 36, "cartoon_mushroom_yellow.png");
    }

    private void AddRotatingLog(double x, double y, double length, double thickness, double angularVelocity, double initialAngleDeg)
    {
        var log = new RotatingLog(x, y, length, thickness, angularVelocity, initialAngleDeg);
        _rotatingLogs.Add(log);
        RaceCanvas.Children.Add(log.Visual);
    }

    private void AddBumper(double x, double y, double radius, string assetName)
    {
        var bumper = new RaceBumper(x, y, radius, assetName);
        _bumpers.Add(bumper);
        RaceCanvas.Children.Add(bumper.Visual);
    }

    


#endregion

    #region Racer Setup & Start Line

    private void ResetToStartLine()
    {
        _isPlaying = false;
        _gameTimer?.Stop();
        _finishedCount = 0;
        _winners.Clear();

        // Clear existing racers from Canvas & Minimap
        foreach (var r in _racers)
        {
            RaceCanvas.Children.Remove(r.Visual);
            MinimapDotsLayer.Children.Remove(r.MinimapDot);
        }
        _racers.Clear();

        bool exclude = ChkExcludePicked.IsChecked == true;
        var eligible = exclude
            ? _studentService.Students.Where(s => !_studentService.PickedStudentNumbers.Contains(s.Number)).ToList()
            : _studentService.Students.ToList();

        if (eligible.Count == 0)
        {
            eligible = _studentService.Students.ToList();
        }

        int count = eligible.Count;
        if (count == 0) return;

        // Line up side-by-side on the start platform at Y = 120
        double startX = 60;
        double endX = 620;
        double span = (endX - startX);
        double spacing = count > 1 ? span / (count - 1) : span / 2.0;

        for (int i = 0; i < count; i++)
        {
            var student = eligible[i];
            double x = (count == 1) ? 340 : (startX + i * spacing);
            double y = 120;

            var racer = new RaceRacer(student, x, y, 20);
            _racers.Add(racer);

            RaceCanvas.Children.Add(racer.Visual);
            MinimapDotsLayer.Children.Add(racer.MinimapDot);
        }

        UpdateLeaderboard();
        UpdateMinimap();
        UpdateCameraViewport(0, force: true);

        BtnStartRace.IsEnabled = true;
        TxtBtnStartLabel.Text = "시작하기";
    }

    


#endregion

    #region Simulation & Physics Loop

    private void BtnStartRace_Click(object sender, RoutedEventArgs e)
    {
        if (_isPlaying) return;
        StartRaceSimulation();
    }

    private void StartRaceSimulation()
    {
        if (_isPlaying) return;

        // Target count
        _targetWinnerCount = CbWinnerCount.SelectedIndex + 1;
        _finishedCount = 0;
        _winners.Clear();

        var rand = new Random();
        foreach (var r in _racers)
        {
            r.IsFinished = false;
            r.FinishRank = 0;
            r.Vx = (rand.NextDouble() - 0.5) * 80;
            r.Vy = 40 + rand.NextDouble() * 50;
        }

        _isPlaying = true;
        BtnStartRace.IsEnabled = false;
        TxtBtnStartLabel.Text = "레이스 질주 중...";
        _lastFrameTime = DateTime.UtcNow;

        if (_soundEnabled) _soundService.PlayBeep();

        if (_gameTimer == null)
        {
            _gameTimer = new DispatcherTimer(DispatcherPriority.Render)
            {
                Interval = TimeSpan.FromMilliseconds(16) // ~60 FPS
            };
            _gameTimer.Tick += GameTimer_Tick;
        }
        _gameTimer.Start();
    }

    private void GameTimer_Tick(object? sender, EventArgs e)
    {
        var now = DateTime.UtcNow;
        double dt = (now - _lastFrameTime).TotalSeconds * _speedMultiplier;
        _lastFrameTime = now;
        if (dt > 0.06) dt = 0.06;

        double gravity = 320.0;
        double damp = 0.995;
        var rand = new Random();

        // 1. Update Bumpers & Rotating Logs
        foreach (var bumper in _bumpers)
        {
            bumper.Update(dt);
        }
        foreach (var log in _rotatingLogs)
        {
            log.Update(dt);
        }

        // 2. Update Racers
        for (int i = 0; i < _racers.Count; i++)
        {
            var r = _racers[i];
            if (r.IsFinished)
            {
                // Slide down slowly in water chute
                r.Y += 120.0 * dt;
                r.UpdateVisual();
                continue;
            }

            r.Vy += gravity * dt;
            r.Vx *= damp;
            r.Vy *= damp;

            r.Vx = Math.Clamp(r.Vx, -240.0, 240.0);
            r.Vy = Math.Clamp(r.Vy, -160.0, 360.0);

            r.X += r.Vx * dt;
            r.Y += r.Vy * dt;

            // Anti-jam: gently push racers if stuck on a ledge
            if (r.Y > 200 && r.Y < 2000 && Math.Abs(r.Vx) < 5 && Math.Abs(r.Vy) < 15)
            {
                r.Vx += (rand.NextDouble() - 0.5) * 80;
                r.Vy += 40;
            }

            // Left & Right Outer Track Boundaries
            double leftWall = 35;
            double rightWall = 645;
            if (r.X - r.Radius < leftWall)
            {
                r.X = leftWall + r.Radius;
                r.Vx = Math.Abs(r.Vx) * 0.75 + 15;
            }
            else if (r.X + r.Radius > rightWall)
            {
                r.X = rightWall - r.Radius;
                r.Vx = -Math.Abs(r.Vx) * 0.75 - 15;
            }

            // Collisions with Rails
            foreach (var rail in _rails)
            {
                double sx = rail.X2 - rail.X1;
                double sy = rail.Y2 - rail.Y1;
                double lenSq = sx * sx + sy * sy;
                if (lenSq < 0.001) continue;

                double t = ((r.X - rail.X1) * sx + (r.Y - rail.Y1) * sy) / lenSq;
                t = Math.Clamp(t, 0, 1);
                double cx = rail.X1 + t * sx;
                double cy = rail.Y1 + t * sy;
                double dx = r.X - cx;
                double dy = r.Y - cy;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + rail.Thickness;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;
                    r.X += nx * overlap;
                    r.Y += ny * overlap;

                    double dot = r.Vx * nx + r.Vy * ny;
                    if (dot < 0)
                    {
                        r.Vx -= 1.65 * dot * nx;
                        r.Vy -= 1.65 * dot * ny;
                        // Slide tangent nudge
                        r.Vx += -ny * ((rand.NextDouble() - 0.5) * 20);
                        r.Vy += nx * ((rand.NextDouble() - 0.5) * 20);
                    }
                }
            }

            // Collisions with Rotating Logs (회전 통나무 동적 충돌 & 회전력 튕김!)
            foreach (var log in _rotatingLogs)
            {
                if (log.CheckAndResolveCollision(r, rand, out bool collided))
                {
                    if (collided && _soundEnabled)
                    {
                        _soundService.PlayBeep();
                    }
                }
            }

            // Collisions with Bumpers (Mushroom & Rune Stones)
            foreach (var bumper in _bumpers)
            {
                double dx = r.X - bumper.X;
                double dy = r.Y - bumper.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + bumper.Radius;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;
                    r.X += nx * overlap;
                    r.Y += ny * overlap;

                    double dot = r.Vx * nx + r.Vy * ny;
                    if (dot < 0)
                    {
                        double boost = 1.35;
                        r.Vx = (-dot * nx * boost) + (rand.NextDouble() - 0.5) * 50;
                        r.Vy = (-dot * ny * boost) - 60;
                        bumper.Flash();
                        if (_soundEnabled) _soundService.PlayBeep();
                    }
                }
            }

            // Ball-to-Ball Collisions
            for (int j = i + 1; j < _racers.Count; j++)
            {
                var o = _racers[j];
                if (o.IsFinished) continue;

                double dx = o.X - r.X;
                double dy = o.Y - r.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + o.Radius;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;

                    r.X -= nx * overlap * 0.5;
                    r.Y -= ny * overlap * 0.5;
                    o.X += nx * overlap * 0.5;
                    o.Y += ny * overlap * 0.5;

                    double kx = r.Vx - o.Vx;
                    double ky = r.Vy - o.Vy;
                    double p = 2 * (nx * kx + ny * ky) / 2.0;

                    r.Vx -= p * nx * 0.7;
                    r.Vy -= p * ny * 0.7;
                    o.Vx += p * nx * 0.7;
                    o.Vy += p * ny * 0.7;
                }
            }

            // 5. Finish Waterfall Chute Crossing
            if (r.Y >= FinishY && r.X >= 230 && r.X <= 450)
            {
                r.IsFinished = true;
                r.FinishRank = ++_finishedCount;
                _winners.Add(r.Student);

                if (_soundEnabled) _soundService.PlayChime();

                if (_finishedCount == _targetWinnerCount)
                {
                    // Winner(s) decided!
                    TriggerWinnerCelebration(r.Student);
                }
            }
            else if (r.Y > 2120)
            {
                // Settled into side trays
                r.IsFinished = true;
                r.FinishRank = ++_finishedCount;
            }

            r.UpdateVisual();
        }

        // Camera Follows Leader
        UpdateCameraViewport(dt);

        // Update Minimap & Leaderboard
        UpdateMinimap();
        UpdateLeaderboard();

        // Check if all racers completed
        if (_racers.All(r => r.IsFinished))
        {
            _gameTimer?.Stop();
            _isPlaying = false;
            BtnStartRace.IsEnabled = true;
            TxtBtnStartLabel.Text = "시작하기";
        }
    }

    private void UpdateCameraViewport(double dt, bool force = false)
    {
        if (RaceViewport == null || RaceScrollViewer == null) return;

        double viewportHeight = RaceViewport.ActualHeight;
        if (viewportHeight <= 1) return;

        // Auto scale to viewport width
        double usableWidth = Math.Max(400, RaceViewport.ActualWidth - 20);
        double scale = Math.Clamp(usableWidth / TrackWidth, 0.7, 1.4);
        RaceWorldScale.ScaleX = scale;
        RaceWorldScale.ScaleY = scale;

        // Find leader
        var leader = _racers.Where(r => !r.IsFinished).OrderByDescending(r => r.Y).FirstOrDefault()
                     ?? _racers.OrderByDescending(r => r.Y).FirstOrDefault();

        double leaderY = leader?.Y ?? 0;
        double targetOffset = Math.Max(0, leaderY * scale - viewportHeight * 0.35);
        double maxOffset = Math.Max(0, TrackHeight * scale - viewportHeight);
        targetOffset = Math.Clamp(targetOffset, 0, maxOffset);

        if (force)
        {
            RaceScrollViewer.ScrollToVerticalOffset(targetOffset);
        }
        else
        {
            double current = RaceScrollViewer.VerticalOffset;
            double alpha = 1.0 - Math.Exp(-6.0 * Math.Max(dt, 0.001));
            RaceScrollViewer.ScrollToVerticalOffset(current + (targetOffset - current) * alpha);
        }
    }

    private void UpdateMinimap()
    {
        if (MinimapCanvas == null || MinimapViewportBox == null) return;

        double mapW = MinimapCanvas.ActualWidth;
        double mapH = MinimapCanvas.ActualHeight;
        if (mapW <= 1 || mapH <= 1) return;

        double scaleX = mapW / TrackWidth;
        double scaleY = mapH / TrackHeight;

        // Update dots
        foreach (var r in _racers)
        {
            Canvas.SetLeft(r.MinimapDot, r.X * scaleX - 3.5);
            Canvas.SetTop(r.MinimapDot, r.Y * scaleY - 3.5);
        }

        // Update camera viewport box on minimap
        if (RaceViewport != null && RaceScrollViewer != null)
        {
            double scrollY = RaceScrollViewer.VerticalOffset / RaceWorldScale.ScaleY;
            double viewH = RaceViewport.ActualHeight / RaceWorldScale.ScaleY;

            Canvas.SetTop(MinimapViewportBox, Math.Clamp(scrollY * scaleY, 0, mapH - 30));
            MinimapViewportBox.Height = Math.Clamp(viewH * scaleY, 20, mapH);
        }
    }

    private void UpdateLeaderboard()
    {
        if (PanelLeaderboard == null) return;
        PanelLeaderboard.Children.Clear();

        // Sort: finished racers by FinishRank, active racers by Y descending
        var sorted = _racers
            .OrderBy(r => r.IsFinished ? 0 : 1)
            .ThenBy(r => r.IsFinished ? r.FinishRank : 0)
            .ThenByDescending(r => r.Y)
            .ToList();

        for (int i = 0; i < sorted.Count; i++)
        {
            var racer = sorted[i];
            int rank = i + 1;

            var row = new Grid
            {
                Margin = new Thickness(0, 2, 0, 2),
                Height = 32
            };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(28) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            // Rank Badge: Gold for 1, Silver for 2, Bronze for 3, Grey for rest
            string badgeColor = rank switch
            {
                1 => "#EAB308",
                2 => "#94A3B8",
                3 => "#D97706",
                _ => "#3F3F46"
            };

            var badge = new Border
            {
                Width = 22,
                Height = 22,
                CornerRadius = new CornerRadius(11),
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(badgeColor)),
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            badge.Child = new TextBlock
            {
                Text = $"{rank}",
                FontSize = 11,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.White,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            Grid.SetColumn(badge, 0);
            row.Children.Add(badge);

            // Animal Avatar
            var avatarImg = new Image
            {
                Width = 24,
                Height = 24,
                Source = AnimalAvatarCatalog.GetAvatarBitmap(racer.Student.EffectiveAvatarId),
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            Grid.SetColumn(avatarImg, 1);
            row.Children.Add(avatarImg);

            // Student Name
            var nameText = new TextBlock
            {
                Text = racer.Student.Name,
                FontSize = 12,
                FontWeight = rank <= 3 ? FontWeights.Bold : FontWeights.Normal,
                Foreground = rank == 1 ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")) : Brushes.White,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(6, 0, 0, 0),
                TextTrimming = TextTrimming.CharacterEllipsis
            };
            Grid.SetColumn(nameText, 2);
            row.Children.Add(nameText);

            PanelLeaderboard.Children.Add(row);
        }
    }

    private void TriggerWinnerCelebration(StudentItem winner)
    {
        _studentService.PickedStudentNumbers.Add(winner.Number);

        TxtWinnerTitle.Text = $"{winner.Number}번 {winner.Name} ({winner.AvatarName})";
        ImgWinnerAvatar.Source = AnimalAvatarCatalog.GetAvatarBitmap(winner.EffectiveAvatarId);

        GridCelebration.Visibility = Visibility.Visible;
    }

    private void DismissCelebration()
    {
        GridCelebration.Visibility = Visibility.Collapsed;
    }

    private void BtnDismissCelebration_Click(object sender, RoutedEventArgs e) => DismissCelebration();

    private void BtnNextLaunch_Click(object sender, RoutedEventArgs e)
    {
        DismissCelebration();
        ResetToStartLine();
        StartRaceSimulation();
    }

    


#endregion

    #region Window UI Controls

    private void BtnResetToStart_Click(object sender, RoutedEventArgs e)
    {
        ResetToStartLine();
    }

    private void BtnInitAll_Click(object sender, RoutedEventArgs e)
    {
        _studentService.ResetPicked();
        ResetToStartLine();
        MessageBox.Show("추첨 기록 및 제외 명단이 초기화되었습니다.", "초기화", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void BtnSpeedToggle_Click(object sender, RoutedEventArgs e)
    {
        if (_speedMultiplier < 1.4)
        {
            _speedMultiplier = 1.8;
            BtnSpeedToggle.Content = "> 2x";
        }
        else if (_speedMultiplier < 2.2)
        {
            _speedMultiplier = 2.6;
            BtnSpeedToggle.Content = "> 3x";
        }
        else
        {
            _speedMultiplier = 1.0;
            BtnSpeedToggle.Content = "> 1x";
        }
    }

    private void BtnSoundToggle_Click(object sender, RoutedEventArgs e)
    {
        _soundEnabled = !_soundEnabled;
        BtnSoundToggle.Content = _soundEnabled ? "🔊" : "🔇";
    }

    private void BtnHideTitle_Click(object sender, RoutedEventArgs e)
    {
        if (TbRaceTitle.Visibility == Visibility.Visible)
        {
            TbRaceTitle.Visibility = Visibility.Collapsed;
            BtnHideTitle.Content = "제목 보이기";
        }
        else
        {
            TbRaceTitle.Visibility = Visibility.Visible;
            BtnHideTitle.Content = "제목 숨기기";
        }
    }

    private void BtnViewResult_Click(object sender, RoutedEventArgs e)
    {
        if (_winners.Count > 0)
        {
            TriggerWinnerCelebration(_winners.First());
        }
        else
        {
            var first = _racers.OrderBy(r => r.IsFinished ? r.FinishRank : 999).ThenByDescending(r => r.Y).FirstOrDefault();
            if (first != null)
            {
                TriggerWinnerCelebration(first.Student);
            }
        }
    }

    private void BtnManageRoster_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new StudentRosterManageDialog(_studentService)
        {
            Owner = this
        };
        if (dlg.ShowDialog() == true)
        {
            ResetToStartLine();
        }
    }

    private void RaceViewport_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        UpdateCameraViewport(0, force: true);
        UpdateMinimap();
    }

    private void RaceScrollViewer_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
    {
        // Allow teacher to freely scroll the race track
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        _gameTimer?.Stop();
        e.Cancel = true;
        Hide();
    }

    


#endregion
}

#region Helper Physics & Graphic Classes

public class RaceRacer
{
    public StudentItem Student { get; }
    public double X { get; set; }
    public double Y { get; set; }
    public double Vx { get; set; }
    public double Vy { get; set; }
    public double Radius { get; }
    public bool IsFinished { get; set; } = false;
    public int FinishRank { get; set; } = 0;

    public Grid Visual { get; }
    public Ellipse MinimapDot { get; }
    private readonly RotateTransform _rot;

    public RaceRacer(StudentItem student, double x, double y, double radius)
    {
        Student = student;
        X = x;
        Y = y;
        Radius = radius;

        Visual = new Grid
        {
            Width = radius * 2 + 30,
            Height = radius * 2 + 26
        };

        _rot = new RotateTransform(0);
        Visual.RenderTransformOrigin = new Point(0.5, 0.4);
        Visual.RenderTransform = _rot;

        // 1. Natural Animal Avatar (FRAMELESS - No circular frame or thick stroke!)
        var img = new Image
        {
            Width = radius * 2 + 4,
            Height = radius * 2 + 4,
            Source = AnimalAvatarCatalog.GetAvatarBitmap(student.EffectiveAvatarId),
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Top,
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        Visual.Children.Add(img);

        // 2. Translucent Black Pill Badge with Student Name
        var badge = new Border
        {
            Background = new SolidColorBrush(Color.FromArgb(215, 15, 23, 42)),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(6, 1, 6, 1),
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Bottom,
            Margin = new Thickness(0, 0, 0, 0)
        };
        badge.Child = new TextBlock
        {
            Text = student.Name,
            FontSize = 10,
            FontWeight = FontWeights.Bold,
            Foreground = Brushes.White,
            HorizontalAlignment = HorizontalAlignment.Center
        };
        Visual.Children.Add(badge);

        // 3. Minimap Dot
        MinimapDot = new Ellipse
        {
            Width = 7,
            Height = 7,
            Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")),
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B45309")),
            StrokeThickness = 1
        };

        UpdateVisual();
    }

    public void UpdateVisual()
    {
        Canvas.SetLeft(Visual, X - Visual.Width / 2.0);
        Canvas.SetTop(Visual, Y - Radius);

        // Tilt based on horizontal velocity
        double angle = Math.Clamp(Vx * 0.15, -28.0, 28.0);
        _rot.Angle = angle;
    }
}

public class RaceRail
{
    public double X1 { get; }
    public double Y1 { get; }
    public double X2 { get; }
    public double Y2 { get; }
    public double Thickness { get; }

    public RaceRail(double x1, double y1, double x2, double y2, double thickness)
    {
        X1 = x1;
        Y1 = y1;
        X2 = x2;
        Y2 = y2;
        Thickness = thickness;
    }
}

public class RaceBumper
{
    public double X { get; }
    public double Y { get; }
    public double Radius { get; }
    public Grid Visual { get; }
    private double _flashTimer;
    private readonly ScaleTransform _scale;

    public RaceBumper(double x, double y, double radius, string assetName)
    {
        X = x;
        Y = y;
        Radius = radius;

        Visual = new Grid
        {
            Width = radius * 2,
            Height = radius * 2
        };

        _scale = new ScaleTransform(1, 1);
        Visual.RenderTransformOrigin = new Point(0.5, 0.5);
        Visual.RenderTransform = _scale;

        var img = new Image
        {
            Width = radius * 2,
            Height = radius * 2,
            Source = new BitmapImage(new Uri($"pack://application:,,,/assets/race/{assetName}")),
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        Visual.Children.Add(img);

        Canvas.SetLeft(Visual, x - radius);
        Canvas.SetTop(Visual, y - radius);
    }

    public void Flash()
    {
        _flashTimer = 0.25;
        _scale.ScaleX = 1.25;
        _scale.ScaleY = 1.25;
    }

    public void Update(double dt)
    {
        if (_flashTimer > 0)
        {
            _flashTimer -= dt;
            if (_flashTimer <= 0)
            {
                _scale.ScaleX = 1.0;
                _scale.ScaleY = 1.0;
            }
        }
    }
}

public class RotatingLog
{
    public double X { get; }
    public double Y { get; }
    public double Length { get; }
    public double Thickness { get; }
    public double AngularVelocity { get; set; } // rad/s
    public double Angle { get; private set; } // radians

    public Grid Visual { get; }
    private readonly RotateTransform _rotateTransform;

    public RotatingLog(double x, double y, double length, double thickness, double angularVelocity, double initialAngleDeg = 0)
    {
        X = x;
        Y = y;
        Length = length;
        Thickness = thickness;
        AngularVelocity = angularVelocity;
        Angle = initialAngleDeg * Math.PI / 180.0;

        Visual = new Grid
        {
            Width = length,
            Height = thickness * (100.0 / 56.0),
        };

        _rotateTransform = new RotateTransform(initialAngleDeg);
        Visual.RenderTransformOrigin = new Point(0.5, 0.5);
        Visual.RenderTransform = _rotateTransform;

        var img = new Image
        {
            Width = length,
            Height = Visual.Height,
            Source = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_log_rotating.png")),
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        Visual.Children.Add(img);

        Canvas.SetLeft(Visual, X - Visual.Width / 2.0);
        Canvas.SetTop(Visual, Y - Visual.Height / 2.0);
    }

    public void Update(double dt)
    {
        Angle += AngularVelocity * dt;
        while (Angle > Math.PI) Angle -= 2 * Math.PI;
        while (Angle < -Math.PI) Angle += 2 * Math.PI;
        _rotateTransform.Angle = Angle * 180.0 / Math.PI;
    }

    public bool CheckAndResolveCollision(RaceRacer r, Random rand, out bool collided)
    {
        collided = false;
        double halfL = Length * 0.44;
        double halfT = Thickness * 0.5;

        double cosA = Math.Cos(Angle);
        double sinA = Math.Sin(Angle);

        double p1x = X - halfL * cosA;
        double p1y = Y - halfL * sinA;
        double p2x = X + halfL * cosA;
        double p2y = Y + halfL * sinA;

        double sx = p2x - p1x;
        double sy = p2y - p1y;
        double lenSq = sx * sx + sy * sy;
        if (lenSq < 0.001) return false;

        double t = ((r.X - p1x) * sx + (r.Y - p1y) * sy) / lenSq;
        t = Math.Clamp(t, 0.0, 1.0);

        double cx = p1x + t * sx;
        double cy = p1y + t * sy;

        double dx = r.X - cx;
        double dy = r.Y - cy;
        double dist = Math.Sqrt(dx * dx + dy * dy);
        double minDist = r.Radius + halfT;

        if (dist < minDist)
        {
            collided = true;
            double nx, ny;
            if (dist > 0.001)
            {
                nx = dx / dist;
                ny = dy / dist;
            }
            else
            {
                nx = -sinA;
                ny = cosA;
            }

            // Push out
            double overlap = minDist - dist + 1.0;
            r.X += nx * overlap;
            r.Y += ny * overlap;

            // Rotational linear velocity at contact point (cx, cy)
            double rx = cx - X;
            double ry = cy - Y;
            double logVx = -AngularVelocity * ry;
            double logVy = AngularVelocity * rx;

            // Relative velocity
            double relVx = r.Vx - logVx;
            double relVy = r.Vy - logVy;

            double normVel = relVx * nx + relVy * ny;
            if (normVel < 0)
            {
                double restitution = 1.35; // energetic cartoon bounce
                double impulse = -(1.0 + restitution) * normVel;
                double newRelVx = relVx + impulse * nx;
                double newRelVy = relVy + impulse * ny;

                r.Vx = logVx + newRelVx + (rand.NextDouble() - 0.5) * 40;
                r.Vy = logVy + newRelVy + 15;
            }
            return true;
        }
        return false;
    }
}

#endregion

