using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Media;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
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
    private readonly List<PoppableBubble> _bubbles = new();
    private readonly List<PopOutSquirrel> _squirrels = new();
    private readonly List<ThrownProjectile> _projectiles = new();

    private DispatcherTimer? _gameTimer;
    private bool _isPlaying = false;
    private bool _soundEnabled = false;
    private double _speedMultiplier = 1.0;
    private double _raceElapsedSeconds = 0;
    private DateTime _lastFrameTime = DateTime.UtcNow;
    private SoundPlayer? _bgmPlayer;

    private const double TrackWidth = 680.0;
    private const double TrackHeight = 3500.0;
    private const double FinishY = 3360.0;
    private bool _isPaused = false;
    private int _targetCameraRank = 1; // 1 = 1등(선두/기본), 2 = 2등, ..., 14 = 14등 등
    private int? _targetCameraStudentNumber = null;
    private double _leaderboardThrottleTimer = 0;

    public static void GetTrackBoundaries(double y, out double left, out double right)
    {
        if (y <= 160.0)
        {
            left = 50.0;
            right = 630.0;
        }
        else if (y <= 420.0)
        {
            // Meadow chicane
            double t = (y - 160.0) / (420.0 - 160.0);
            double c = 340.0 + 35.0 * Math.Sin(t * Math.PI * 2.0);
            double hw = 290.0 - 50.0 * t;
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 560.0)
        {
            // Bridge funnel into canyon
            double t = (y - 420.0) / (560.0 - 420.0);
            double s = t * t * (3.0 - 2.0 * t);
            double c = 340.0;
            double hw = 240.0 - 80.0 * s;
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 950.0)
        {
            // Canyon S-Curve 1: Banking to the LEFT
            double t = (y - 560.0) / (950.0 - 560.0);
            double c = 340.0 - 80.0 * Math.Sin(t * Math.PI);
            double hw = 160.0;
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 1350.0)
        {
            // Canyon S-Curve 2: Banking to the RIGHT
            double t = (y - 950.0) / (1350.0 - 950.0);
            double c = 340.0 + 80.0 * Math.Sin(t * Math.PI);
            double hw = 160.0;
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 1640.0)
        {
            // Fossil Mesa Chutes (Left & Right chutes around fossil)
            double t = (y - 1350.0) / (1640.0 - 1350.0);
            double s = Math.Clamp(t * t * (3.0 - 2.0 * t), 0.0, 1.0);
            left = 180.0 - 40.0 * s;
            right = 500.0 + 40.0 * s;
        }
        else if (y <= 1820.0)
        {
            // Funnel around Upper Diamond (tapers to 170..510)
            double t = (y - 1640.0) / (1820.0 - 1640.0);
            double s = t * t * (3.0 - 2.0 * t);
            left = 140.0 + 30.0 * s;
            right = 540.0 - 30.0 * s;
        }
        else if (y <= 1990.0)
        {
            // Widens around the Two Lower Diamonds
            double t = (y - 1820.0) / (1990.0 - 1820.0);
            double s = Math.Sin(t * Math.PI);
            left = 170.0 - 85.0 * s;
            right = 510.0 + 85.0 * s;
        }
        else if (y <= 2080.0)
        {
            // Maze Exit Funnel
            double t = (y - 1990.0) / (2080.0 - 1990.0);
            double s = t * t * (3.0 - 2.0 * t);
            left = 170.0 - 15.0 * s;
            right = 510.0 + 15.0 * s;
        }
        else if (y <= 2480.0)
        {
            // Forest Meander 1: Banking Right
            double t = (y - 2080.0) / (2480.0 - 2080.0);
            double c = 340.0 + 50.0 * Math.Sin(t * Math.PI);
            double hw = 185.0;
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 3200.0)
        {
            // Forest Meander 2 into River Rapids (stays wide and spacious until 3200!)
            double t = (y - 2480.0) / (3200.0 - 2480.0);
            double c = 340.0 - 30.0 * Math.Sin(t * Math.PI);
            double hw = 185.0; // width 370
            left = c - hw;
            right = c + hw;
        }
        else if (y <= 3320.0)
        {
            // Compact Angled Funnel ("단축된 깔대기 입구 - 기존 240px의 절반인 120px로 단축")
            // Over 120px, smoothly tapers diagonally from width 370 (hw 185) down to 160 (hw 80)
            double t = (y - 3200.0) / (3320.0 - 3200.0);
            double c = 340.0;
            double hw = 185.0 - 105.0 * t; // [155, 525] -> [260, 420]
            left = c - hw;
            right = c + hw;
        }
        else
        {
            // Short Funnel Neck & Harbor Dock (Y = 3320 ~ 3500, width 160)
            double c = 340.0;
            double hw = 80.0; // [260, 420]
            left = c - hw;
            right = c + hw;
        }
    }

    private int _targetWinnerCount = 1;
    private int _finishedCount = 0;
    private readonly List<StudentItem> _winners = new();

    public StudentPickerWindow(IStudentManagerService studentService, ISoundService soundService, IDisplayManager? displayManager = null)
    {
        _studentService = studentService;
        _soundService = soundService;
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        InitializeComponent();

        _soundEnabled = false;
        _soundService.IsMuted = true;
        InitBgmPlayer();

        Loaded += (s, e) =>
        {
            SetupCourseScenery();
            ResetToStartLine();
            PositionToDefaultMonitor();
            UpdateCameraViewport(0, force: true);
            if (SliderSoundVolume != null)
            {
                SliderSoundVolume.Value = 0;
                UpdateSoundUi();
            }
        };

        IsVisibleChanged += (s, e) =>
        {
            if (!IsVisible)
            {
                StopAndReset();
            }
        };

        Closing += (s, e) =>
        {
            StopBgm();
            _soundService.StopAll();
        };

        KeyDown += Window_KeyDown;
    }

    #region Racing BGM Controls

    private void InitBgmPlayer()
    {
        try
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string[] candidates = new[]
            {
                System.IO.Path.Combine(baseDir, "assets", "race", "race_bgm.wav"),
                System.IO.Path.Combine(baseDir, "..", "..", "..", "assets", "race", "race_bgm.wav"),
                System.IO.Path.Combine(Directory.GetCurrentDirectory(), "assets", "race", "race_bgm.wav")
            };
            foreach (var p in candidates)
            {
                if (File.Exists(p))
                {
                    _bgmPlayer = new SoundPlayer(p);
                    _bgmPlayer.LoadAsync();
                    break;
                }
            }
        }
        catch { }
    }

    private void PlayBgm()
    {
        if (!_soundEnabled || _isPaused || !_isPlaying) return;
        try
        {
            _bgmPlayer?.PlayLooping();
        }
        catch { }
    }

    private void StopBgm()
    {
        try
        {
            _bgmPlayer?.Stop();
        }
        catch { }
    }

    #endregion

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
            else if (_isPlaying)
            {
                TogglePause();
            }
            else
            {
                StartRaceSimulation();
            }
            e.Handled = true;
        }
        else if (e.Key == Key.PageUp || e.Key == Key.Up)
        {
            if (TbRaceTitle == null || !TbRaceTitle.IsKeyboardFocused)
            {
                SetCameraRank(_targetCameraRank - 1);
                e.Handled = true;
            }
        }
        else if (e.Key == Key.PageDown || e.Key == Key.Down)
        {
            if (TbRaceTitle == null || !TbRaceTitle.IsKeyboardFocused)
            {
                SetCameraRank(_targetCameraRank + 1);
                e.Handled = true;
            }
        }
        else if (e.Key == Key.Home)
        {
            if (TbRaceTitle == null || !TbRaceTitle.IsKeyboardFocused)
            {
                SetCameraRank(1);
                e.Handled = true;
            }
        }
        else if (e.Key == Key.Escape)
        {
            if (GridCelebration.Visibility == Visibility.Visible)
            {
                DismissCelebration();
            }
            else
            {
                StopAndReset();
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
        foreach (var bub in _bubbles) RaceCanvas.Children.Remove(bub.Visual);
        foreach (var sq in _squirrels)
        {
            RaceCanvas.Children.Remove(sq.BranchVisual);
            RaceCanvas.Children.Remove(sq.SquirrelVisual);
        }
        foreach (var p in _projectiles) RaceCanvas.Children.Remove(p.Visual);
        _bumpers.Clear();
        _rails.Clear();
        _rotatingLogs.Clear();
        _bubbles.Clear();
        _squirrels.Clear();
        _projectiles.Clear();

        // 1. Zone 3 Dinosaur Fossil Mesa & Diamond Maze Guide Rails
        // A. Dinosaur Fossil Mesa (Y = 1360 ~ 1640)
        _rails.Add(new RaceRail(340, 1360, 260, 1440, 14));
        _rails.Add(new RaceRail(340, 1360, 420, 1440, 14));
        _rails.Add(new RaceRail(260, 1440, 260, 1570, 14));
        _rails.Add(new RaceRail(420, 1440, 420, 1570, 14));
        _rails.Add(new RaceRail(260, 1570, 340, 1640, 14));
        _rails.Add(new RaceRail(420, 1570, 340, 1640, 14));

        // B. Upper Center Diamond Rock (Y = 1680 ~ 1810)
        _rails.Add(new RaceRail(340, 1680, 304, 1745, 14));
        _rails.Add(new RaceRail(340, 1680, 376, 1745, 14));
        _rails.Add(new RaceRail(304, 1745, 340, 1810, 14));
        _rails.Add(new RaceRail(376, 1745, 340, 1810, 14));

        // C. Lower-Left Diamond Rock (Y = 1830 ~ 1975)
        _rails.Add(new RaceRail(230, 1830, 198, 1905, 14));
        _rails.Add(new RaceRail(230, 1830, 262, 1905, 14));
        _rails.Add(new RaceRail(198, 1905, 230, 1975, 14));
        _rails.Add(new RaceRail(262, 1905, 230, 1975, 14));

        // D. Lower-Right Diamond Rock (Y = 1830 ~ 1975)
        _rails.Add(new RaceRail(450, 1830, 418, 1905, 14));
        _rails.Add(new RaceRail(450, 1830, 482, 1905, 14));
        _rails.Add(new RaceRail(418, 1905, 450, 1975, 14));
        _rails.Add(new RaceRail(482, 1905, 450, 1975, 14));

        // 2. ROTATING LOGS (회전 통나무 동적 장애물 - 폭을 110px로 최적화하여 좌우 통로 120px 이상 완전 개방)
        // Upper Canyon Chicane: Clockwise Rotating Log
        AddRotatingLog(275, 680, 110, 22, 2.2, 15);

        // Fossil Mesa Twin Rapids Pebble Bumpers (시원하게 통과할 수 있도록 소형 조약돌 범퍼 배치 - 무병목 보장)
        AddBumper(195, 1540, 13, "cartoon_pebble_bumper.png");
        AddBumper(485, 1540, 13, "cartoon_pebble_bumper.png");

        // Lower Mushroom Forest: Heavy Rotating Log
        AddRotatingLog(380, 2180, 110, 22, -2.0, 0);

        // 3. SMALL CARTOON BUMPERS & OBSTACLES (충분한 최소 간격을 보장하는 최적 분산 배치)
        // --- Meadow & Early Forest (Y = 240 ~ 600) ---
        AddBumper(210, 260, 14, "cartoon_acorn_peg.png");
        AddBumper(470, 260, 14, "cartoon_acorn_peg.png");
        AddBumper(340, 330, 15, "cartoon_wood_stump.png");
        AddBumper(180, 410, 16, "cartoon_flower_bumper.png");
        AddBumper(500, 410, 16, "cartoon_flower_bumper.png");
        AddBumper(340, 500, 15, "cartoon_wood_stump.png");

        // --- Canyon Winding Trail (Y = 620 ~ 1350) ---
        AddBumper(210, 640, 14, "cartoon_acorn_peg.png");
        AddBumper(380, 640, 14, "cartoon_acorn_peg.png");
        AddBumper(190, 820, 15, "cartoon_mushroom_purple.png");
        AddBumper(350, 820, 15, "cartoon_mushroom_red.png");
        AddBumper(290, 1000, 14, "cartoon_pebble_bumper.png");
        AddBumper(460, 1000, 14, "cartoon_pebble_bumper.png");
        AddBumper(340, 1180, 15, "cartoon_wood_stump.png");

        // --- Fossil Mesa & Diamond Maze (Y = 1360 ~ 2080) ---
        // 슬라럼 통로 내부 장애물 전면 제거: 공들이 시원하게 미끄러져 통과할 수 있도록 최소 110px 이상 완전 개방!
        // 미로 출구 유도 범퍼만 배치 (중앙 260px 완전 개방)
        AddBumper(210, 2030, 15, "cartoon_flower_bumper.png");
        AddBumper(470, 2030, 15, "cartoon_flower_bumper.png");

        // --- Enchanted Mushroom Forest (Y = 2100 ~ 2780) ---
        AddBumper(280, 2320, 16, "cartoon_mushroom_red.png");
        AddBumper(480, 2320, 16, "cartoon_mushroom_purple.png");
        AddBumper(230, 2520, 16, "cartoon_flower_bumper.png");
        AddBumper(410, 2520, 16, "cartoon_wood_stump.png");
        AddBumper(340, 2700, 15, "cartoon_mushroom_yellow.png");

        // --- 4. River Rapids Flume & Short Finish Canal (Y = 2800 ~ 3360) ---
        // 넓은 강물 급류 (가장자리 조약돌 2개, 중앙 240px 완전 개방)
        AddBumper(210, 2960, 14, "cartoon_pebble_bumper.png");
        AddBumper(470, 2960, 14, "cartoon_pebble_bumper.png");

        // 단축된 도착 구간 깔대기 직후(Y=3330)의 3개 비눗방울 관문 (도착 직전 3개로 충분!)
        AddBubble(295, 3330, 20);
        AddBubble(340, 3330, 22);
        AddBubble(385, 3330, 20);

        // --- 5. Perched Animated Squirrels (5마리 청설모 솔방울 표창 투척) ---
        AddSquirrel(x: 95, y: 780, radius: 26, isFacingRight: true, startDelay: 0.3, projectileAsset: "cartoon_pinecone_shuriken.png");
        AddSquirrel(x: 585, y: 1150, radius: 26, isFacingRight: false, startDelay: 0.7, projectileAsset: "cartoon_pinecone_shuriken.png");
        AddSquirrel(x: 135, y: 1520, radius: 26, isFacingRight: true, startDelay: 0.5, projectileAsset: "cartoon_pinecone_shuriken.png");
        AddSquirrel(x: 530, y: 1720, radius: 26, isFacingRight: false, startDelay: 0.9, projectileAsset: "cartoon_pinecone_shuriken.png");
        AddSquirrel(x: 195, y: 2320, radius: 26, isFacingRight: true, startDelay: 0.4, projectileAsset: "cartoon_pinecone_shuriken.png");
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

    private void AddBubble(double x, double y, double radius)
    {
        var bubble = new PoppableBubble(x, y, radius);
        _bubbles.Add(bubble);
        RaceCanvas.Children.Add(bubble.Visual);
    }

    private void AddSquirrel(double x, double y, double radius, bool isFacingRight, double startDelay, string projectileAsset)
    {
        var sq = new PopOutSquirrel(x, y, radius, isFacingRight, startDelay, projectileAsset);
        sq.OnThrowProjectile = (proj) =>
        {
            _projectiles.Add(proj);
            RaceCanvas.Children.Add(proj.Visual);
        };
        _squirrels.Add(sq);
        RaceCanvas.Children.Add(sq.BranchVisual);
        RaceCanvas.Children.Add(sq.SquirrelVisual);
    }

    


#endregion

    #region Racer Setup & Start Line

    private void ResetToStartLine()
    {
        StopBgm();
        _soundService.StopAll();
        _isPlaying = false;
        _isPaused = false;
        _gameTimer?.Stop();
        _finishedCount = 0;
        _winners.Clear();
        _raceElapsedSeconds = 0;

        if (BtnPauseResume != null) BtnPauseResume.IsEnabled = false;
        if (TxtPauseIcon != null) TxtPauseIcon.Text = "⏸ ";
        if (TxtPauseLabel != null) TxtPauseLabel.Text = "일시정지";
        if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Collapsed;

        foreach (var b in _bubbles)
        {
            b.Reset();
        }

        foreach (var sq in _squirrels)
        {
            sq.Reset();
        }

        foreach (var p in _projectiles)
        {
            RaceCanvas.Children.Remove(p.Visual);
        }
        _projectiles.Clear();

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

        // Line up side-by-side on the start platform at Y = 135
        double startX = 60;
        double endX = 620;
        double span = (endX - startX);
        double spacing = count > 1 ? span / (count - 1) : span / 2.0;

        for (int i = 0; i < count; i++)
        {
            var student = eligible[i];
            double x = (count == 1) ? 340 : (startX + i * spacing);
            double y = 135;

            var racer = new RaceRacer(student, x, y, 13);
            int studentNum = student.Number;
            racer.Visual.MouseLeftButtonDown += (s, e) =>
            {
                SetCameraTargetStudent(studentNum);
            };
            _racers.Add(racer);

            RaceCanvas.Children.Add(racer.Visual);
            MinimapDotsLayer.Children.Add(racer.MinimapDot);
        }

        UpdateCameraRankOptions();
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

    private void BtnPauseResume_Click(object sender, RoutedEventArgs e)
    {
        TogglePause();
    }

    private void TogglePause()
    {
        if (!_isPlaying) return;
        if (_isPaused)
        {
            ResumeRace();
        }
        else
        {
            PauseRace();
        }
    }

    private void PauseRace()
    {
        if (!_isPlaying || _isPaused) return;
        _isPaused = true;
        StopBgm();
        _soundService.StopAll();
        if (TxtPauseIcon != null) TxtPauseIcon.Text = "▶ ";
        if (TxtPauseLabel != null) TxtPauseLabel.Text = "이어하기";
        if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Visible;
    }

    private void ResumeRace()
    {
        if (!_isPlaying || !_isPaused) return;
        _isPaused = false;
        _lastFrameTime = DateTime.UtcNow;
        if (_soundEnabled) PlayBgm();
        if (TxtPauseIcon != null) TxtPauseIcon.Text = "⏸ ";
        if (TxtPauseLabel != null) TxtPauseLabel.Text = "일시정지";
        if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Collapsed;
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
        _isPaused = false;
        BtnStartRace.IsEnabled = false;
        TxtBtnStartLabel.Text = "레이스 질주 중...";
        if (BtnPauseResume != null) BtnPauseResume.IsEnabled = true;
        if (TxtPauseIcon != null) TxtPauseIcon.Text = "⏸ ";
        if (TxtPauseLabel != null) TxtPauseLabel.Text = "일시정지";
        if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Collapsed;

        _lastFrameTime = DateTime.UtcNow;

        if (_soundEnabled && IsVisible)
        {
            PlayBgm();
        }

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
        if (!_isPlaying || _isPaused || !IsVisible) return;

        var now = DateTime.UtcNow;
        double dt = (now - _lastFrameTime).TotalSeconds * _speedMultiplier;
        _lastFrameTime = now;
        if (dt > 0.06) dt = 0.06;

        double gravity = 320.0;
        double damp = 0.995;
        var rand = new Random();

        _raceElapsedSeconds += dt;

        // 1. Update Bumpers, Rotating Logs & Bubbles
        foreach (var bumper in _bumpers)
        {
            bumper.Update(dt);
        }
        foreach (var log in _rotatingLogs)
        {
            log.Update(dt);
        }
        foreach (var bubble in _bubbles)
        {
            bubble.Update(_raceElapsedSeconds);
        }
        foreach (var sq in _squirrels)
        {
            bool hasTargetApproaching = _racers.Any(r => !r.IsFinished && r.PinnedTimer <= 0 && (r.Y >= sq.Y - 110.0 && r.Y <= sq.Y + 50.0));
            sq.Update(dt, hasTargetApproaching);
        }
        for (int pIdx = _projectiles.Count - 1; pIdx >= 0; pIdx--)
        {
            var proj = _projectiles[pIdx];
            proj.Update(dt);
            if (proj.IsDestroyed)
            {
                RaceCanvas.Children.Remove(proj.Visual);
                _projectiles.RemoveAt(pIdx);
            }
        }

        // 2. Update Racers
        for (int i = 0; i < _racers.Count; i++)
        {
            var r = _racers[i];
            if (r.IsFinished)
            {
                // Slide down smoothly onto harbor dock
                if (r.Y < 3450)
                {
                    r.Y += 100.0 * dt;
                }
                r.UpdateVisual();
                continue;
            }

            if (r.PinnedTimer > 0)
            {
                // Locked to the wall by embedded shuriken pinecone!
                r.PinnedTimer -= dt;
                GetTrackBoundaries(r.Y, out double pLeft, out double pRight);
                if (r.PinnedSide < 0)
                {
                    r.X = pLeft + r.Radius;
                }
                else
                {
                    r.X = pRight - r.Radius;
                }
                r.Vx = 0;
                r.Vy = 0;

                if (r.PinnedTimer <= 0)
                {
                    r.Unpin();
                }

                r.UpdateVisual();
                continue; // Skip collisions and gravity while pinned to wall, allowing smooth overtaking!
            }

            r.Vy += gravity * dt;
            r.Vx *= damp;
            r.Vy *= damp;

            if (r.IsBlownByPinecone)
            {
                r.Vx = Math.Clamp(r.Vx, -620.0, 620.0);
                r.Vy = Math.Clamp(r.Vy, -40.0, 60.0);
            }
            else
            {
                r.Vx = Math.Clamp(r.Vx, -240.0, 240.0);
                r.Vy = Math.Clamp(r.Vy, -160.0, 360.0);
            }

            r.X += r.Vx * dt;
            r.Y += r.Vy * dt;

            // Anti-jam & flow watchdog: actively propel any racer getting slow or stuck above finish
            if (r.Y > 160 && r.Y < FinishY)
            {
                if (r.Vy < 35.0 && r.PinnedTimer <= 0)
                {
                    r.Vy += 90.0 * dt; // Gentle forward drive ensuring zero bottlenecks
                }

                if (Math.Abs(r.Vx) < 14.0 && r.Vy < 35.0)
                {
                    r.StuckTimer += dt;
                    if (r.StuckTimer > 0.20)
                    {
                        // Direct impulse downhill toward the track center
                        double centerNudge = (340.0 - r.X);
                        r.Vx += Math.Sign(centerNudge) * (50.0 + rand.NextDouble() * 30.0);
                        r.Vy = Math.Max(r.Vy + 90.0, 140.0 + rand.NextDouble() * 60.0);
                        r.StuckTimer = 0;
                    }
                }
                else
                {
                    r.StuckTimer = 0;
                }
            }

            // 1. Continuous Outer Track Boundaries (Zero wall penetration & Funnel sliding assist)
            GetTrackBoundaries(r.Y, out double leftWall, out double rightWall);
            if (r.X - r.Radius < leftWall)
            {
                r.X = leftWall + r.Radius;
                if (r.IsBlownByPinecone)
                {
                    // Pinned to the left wall like a target hit by a shuriken!
                    r.PinToWall(-1, 1.35);
                }
                else
                {
                    // Regular bouncy wall collision (끝의 깔대기 구간도 미끄러지지 않고 기존 벽면처럼 통-! 튕김)
                    r.Vx = Math.Abs(r.Vx) * 0.8 + 35.0;
                }
            }
            else if (r.X + r.Radius > rightWall)
            {
                r.X = rightWall - r.Radius;
                if (r.IsBlownByPinecone)
                {
                    // Pinned to the right wall like a target hit by a shuriken!
                    r.PinToWall(1, 1.35);
                }
                else
                {
                    // Regular bouncy wall collision (끝의 깔대기 구간도 미끄러지지 않고 기존 벽면처럼 통-! 튕김)
                    r.Vx = -Math.Abs(r.Vx) * 0.8 - 35.0;
                }
            }

            // 2. Island Collision Watchdogs (Fossil Mesa & 3 Diamond Rocks)
            // Prevents racers from penetrating inside island geometries even at extreme velocities!
            // Island 1: Dinosaur Fossil Mesa (Y: 1360 ~ 1640)
            if (r.Y >= 1360.0 && r.Y <= 1640.0)
            {
                double halfW;
                if (r.Y <= 1440.0)
                {
                    double t = (r.Y - 1360.0) / 80.0;
                    halfW = 80.0 * Math.Clamp(t, 0.0, 1.0);
                }
                else if (r.Y <= 1570.0)
                {
                    halfW = 80.0;
                }
                else
                {
                    double t = (1640.0 - r.Y) / 70.0;
                    halfW = 80.0 * Math.Clamp(t, 0.0, 1.0);
                }

                double islandLeft = 340.0 - halfW;
                double islandRight = 340.0 + halfW;
                if (r.X + r.Radius > islandLeft && r.X - r.Radius < islandRight)
                {
                    if (r.X < 340.0)
                    {
                        r.X = islandLeft - r.Radius;
                        r.Vx = -Math.Abs(r.Vx) * 0.8 - 30.0;
                    }
                    else
                    {
                        r.X = islandRight + r.Radius;
                        r.Vx = Math.Abs(r.Vx) * 0.8 + 30.0;
                    }
                    r.Vy = Math.Max(r.Vy, 70.0);
                }
            }

            // Island 2: Upper Center Diamond Rock (Y: 1680 ~ 1810)
            if (r.Y >= 1680.0 && r.Y <= 1810.0)
            {
                double halfW = (r.Y <= 1745.0)
                    ? 36.0 * (r.Y - 1680.0) / 65.0
                    : 36.0 * (1810.0 - r.Y) / 65.0;
                halfW = Math.Max(0.0, halfW);

                double islandLeft = 340.0 - halfW;
                double islandRight = 340.0 + halfW;
                if (r.X + r.Radius > islandLeft && r.X - r.Radius < islandRight)
                {
                    if (r.X < 340.0)
                    {
                        r.X = islandLeft - r.Radius;
                        r.Vx = -Math.Abs(r.Vx) * 0.8 - 30.0;
                    }
                    else
                    {
                        r.X = islandRight + r.Radius;
                        r.Vx = Math.Abs(r.Vx) * 0.8 + 30.0;
                    }
                    r.Vy = Math.Max(r.Vy, 70.0);
                }
            }

            // Island 3 & 4: Lower Dual Diamond Rocks (Y: 1830 ~ 1975)
            if (r.Y >= 1830.0 && r.Y <= 1975.0)
            {
                double halfW = (r.Y <= 1905.0)
                    ? 32.0 * (r.Y - 1830.0) / 75.0
                    : 32.0 * (1975.0 - r.Y) / 70.0;
                halfW = Math.Max(0.0, halfW);

                // Left Diamond (Center X = 230)
                double leftD_Left = 230.0 - halfW;
                double leftD_Right = 230.0 + halfW;
                if (r.X + r.Radius > leftD_Left && r.X - r.Radius < leftD_Right)
                {
                    if (r.X < 230.0)
                    {
                        r.X = leftD_Left - r.Radius;
                        r.Vx = -Math.Abs(r.Vx) * 0.8 - 25.0;
                    }
                    else
                    {
                        r.X = leftD_Right + r.Radius;
                        r.Vx = Math.Abs(r.Vx) * 0.8 + 25.0;
                    }
                    r.Vy = Math.Max(r.Vy, 70.0);
                }

                // Right Diamond (Center X = 450)
                double rightD_Left = 450.0 - halfW;
                double rightD_Right = 450.0 + halfW;
                if (r.X + r.Radius > rightD_Left && r.X - r.Radius < rightD_Right)
                {
                    if (r.X < 450.0)
                    {
                        r.X = rightD_Left - r.Radius;
                        r.Vx = -Math.Abs(r.Vx) * 0.8 - 25.0;
                    }
                    else
                    {
                        r.X = rightD_Right + r.Radius;
                        r.Vx = Math.Abs(r.Vx) * 0.8 + 25.0;
                    }
                    r.Vy = Math.Max(r.Vy, 70.0);
                }
            }

            // Collisions with Rails (with active downhill sliding!)
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

                if (dist < minDist && dist > 0.0001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist + 0.5;
                    r.X += nx * overlap;
                    r.Y += ny * overlap;

                    // Downhill unit tangent vector (ensure ty >= 0 so it points down the slope)
                    double len = Math.Sqrt(lenSq);
                    double tx = sx / len;
                    double ty = sy / len;
                    if (ty < 0) { tx = -tx; ty = -ty; }

                    // Zero out incoming velocity into normal
                    double dot = r.Vx * nx + r.Vy * ny;
                    if (dot < 0)
                    {
                        r.Vx -= 1.35 * dot * nx;
                        r.Vy -= 1.35 * dot * ny;
                    }

                    // ACTIVE DOWNHILL SLIDING FORCE:
                    // Accelerate along the rail downhill slope so animals slide effortlessly!
                    double downhillForce = 520.0 * dt;
                    r.Vx += tx * downhillForce;
                    r.Vy += ty * downhillForce;
                }
            }

            // Collisions with Rotating Logs (회전 통나무 동적 충돌 & 회전력 튕김!)
            foreach (var log in _rotatingLogs)
            {
                log.CheckAndResolveCollision(r, rand, out bool _);
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
                        double boost = 1.25;
                        r.Vx = (-dot * nx * boost) + (nx >= 0 ? 32.0 : -32.0);
                        // Ensure balls deflect around the bumper without flying backwards into traffic
                        r.Vy = Math.Max(-dot * ny * boost, 45.0);
                        bumper.Flash();
                    }
                }
            }

            // Collisions with Poppable Water Bubbles ("부딪히면 사라지는 비눗방울")
            foreach (var bubble in _bubbles)
            {
                if (bubble.IsPopped) continue;

                double dx = r.X - bubble.X;
                double dy = r.Y - bubble.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + bubble.Radius;

                if (dist < minDist)
                {
                    // Pop the bubble!
                    bubble.Pop();

                    // Dramatic Race Reversal:
                    // The bubble absorbs forward momentum, deflecting the leader upwards & outwards,
                    // momentarily slowing them down so following racers can slip past and overtake!
                    double nx = dist > 0.001 ? dx / dist : (rand.NextDouble() - 0.5);
                    double ny = dist > 0.001 ? dy / dist : -1.0;

                    // Push out of bubble
                    r.X = bubble.X + nx * (minDist + 2.0);
                    r.Y = bubble.Y + ny * (minDist + 2.0);

                    // Rebound upwards and deflect horizontally
                    r.Vx = nx * (65.0 + rand.NextDouble() * 50.0);
                    r.Vy = -60.0 - rand.NextDouble() * 45.0;
                }
            }

            // Collisions with Pop-out Squirrels ("중간에 잠깐 나왔다 들어갔다하며 방해하는 청설모")
            foreach (var sq in _squirrels)
            {
                if (!sq.IsActive) continue;

                double dx = r.X - sq.CurrentX;
                double dy = r.Y - sq.CurrentY;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + sq.Radius;

                if (dist < minDist)
                {
                    sq.Bump();

                    // Push racer out of squirrel hitbox
                    double nx = dist > 0.001 ? dx / dist : (sq.IsFacingRight ? 1.0 : -1.0);
                    double ny = dist > 0.001 ? dy / dist : -0.5;
                    r.X = sq.CurrentX + nx * (minDist + 2.0);
                    r.Y = sq.CurrentY + ny * (minDist + 2.0);

                    // Energetic deflection towards track center
                    double centerPush = sq.IsFacingRight ? 1.0 : -1.0;
                    r.Vx = centerPush * (120.0 + rand.NextDouble() * 50.0);
                    r.Vy = -40.0 + (rand.NextDouble() - 0.5) * 60.0;
                }
            }

            // Collisions with Thrown Acorns & Pinecones ("표창 솔방울: 맞으면 벽에 꽂히는 넉백 & 고정")
            for (int pIdx = _projectiles.Count - 1; pIdx >= 0; pIdx--)
            {
                var proj = _projectiles[pIdx];
                if (proj.IsDestroyed) continue;

                double dx = r.X - proj.X;
                double dy = r.Y - proj.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = r.Radius + proj.Radius;

                if (dist < minDist)
                {
                    proj.Destroy();
                    RaceCanvas.Children.Remove(proj.Visual);
                    _projectiles.RemoveAt(pIdx);

                    // Skewered by shuriken pinecone! (1타 1피 표창 저격)
                    // The first character hit absorbs the shuriken and is blasted to the outer wall!
                    double pushDir = Math.Sign(proj.Vx);
                    if (pushDir == 0) pushDir = (r.X < 340) ? -1.0 : 1.0;

                    r.IsBlownByPinecone = true;
                    r.PineconePushDir = pushDir;
                    r.Vx = pushDir * 680.0; // High speed shuriken knockback fling to wall
                    r.Vy = 5.0; // Perfectly level horizontal trajectory
                }
            }

            // Ball-to-Ball Collisions
            for (int j = i + 1; j < _racers.Count; j++)
            {
                var o = _racers[j];
                if (o.IsFinished || o.PinnedTimer > 0) continue;
                if (r.PinnedTimer > 0) continue;

                // If one racer is flying from pinecone shuriken impact:
                // Only the primary victim gets pinned to the wall!
                // Any racers in the trajectory are just lightly nudged aside with a cartoon bump, NOT chained/pinned!
                if (r.IsBlownByPinecone || o.IsBlownByPinecone)
                {
                    double bdx = o.X - r.X;
                    double bdy = o.Y - r.Y;
                    double bdist = Math.Sqrt(bdx * bdx + bdy * bdy);
                    double bminDist = r.Radius + o.Radius;
                    if (bdist < bminDist && bdist > 0.001)
                    {
                        if (r.IsBlownByPinecone)
                        {
                            o.Vy += (rand.NextDouble() - 0.5) * 50.0;
                            o.Vx += (rand.NextDouble() - 0.5) * 40.0;
                        }
                        else
                        {
                            r.Vy += (rand.NextDouble() - 0.5) * 50.0;
                            r.Vx += (rand.NextDouble() - 0.5) * 40.0;
                        }
                    }
                    continue;
                }

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

            // 5. Finish Line Crossing (Harbor Dock & Confetti)
            if (r.Y >= FinishY && r.X >= 240 && r.X <= 440)
            {
                r.IsFinished = true;
                r.FinishRank = ++_finishedCount;
                _winners.Add(r.Student);

                TriggerWaterSplash(r.X, r.Y);

                if (_soundEnabled && _isPlaying && !_isPaused && IsVisible) _soundService.PlayChime();

                if (_finishedCount == _targetWinnerCount)
                {
                    // Winner(s) decided!
                    TriggerWinnerCelebration(r.Student);
                }
            }
            else if (r.Y > 3480)
            {
                // Settled into harbor dock platform
                r.IsFinished = true;
                r.FinishRank = ++_finishedCount;
            }

            r.UpdateVisual();
        }

        // Camera Follows Target (1등 기본, 2등, 3등, 14등 등 선택 가능)
        UpdateCameraViewport(dt);

        // Update Minimap & Leaderboard
        UpdateMinimap();
        _leaderboardThrottleTimer += dt;
        if (_leaderboardThrottleTimer >= 0.1)
        {
            UpdateLeaderboard();
            _leaderboardThrottleTimer = 0;
        }

        // Check if all racers completed
        if (_racers.All(r => r.IsFinished))
        {
            _gameTimer?.Stop();
            _isPlaying = false;
            _isPaused = false;
            BtnStartRace.IsEnabled = true;
            TxtBtnStartLabel.Text = "시작하기";
            if (BtnPauseResume != null) BtnPauseResume.IsEnabled = false;
            if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Collapsed;
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

        // Current standings
        var sorted = _racers
            .OrderBy(r => r.IsFinished ? 0 : 1)
            .ThenBy(r => r.IsFinished ? r.FinishRank : 0)
            .ThenByDescending(r => r.Y)
            .ToList();

        if (sorted.Count == 0) return;

        RaceRacer targetRacer;
        if (_targetCameraStudentNumber.HasValue)
        {
            targetRacer = sorted.FirstOrDefault(r => r.Student.Number == _targetCameraStudentNumber.Value)
                          ?? sorted[0];
        }
        else if (_targetCameraRank == 1)
        {
            // Default: active leader (or first finisher if all finished)
            targetRacer = _racers.Where(r => !r.IsFinished).OrderByDescending(r => r.Y).FirstOrDefault()
                          ?? sorted[0];
        }
        else
        {
            int rankIdx = Math.Clamp(_targetCameraRank - 1, 0, sorted.Count - 1);
            targetRacer = sorted[rankIdx];
        }

        // Update camera focus ring on racers
        bool showFocus = (_targetCameraRank > 1 || _targetCameraStudentNumber.HasValue);
        foreach (var r in _racers)
        {
            r.SetCameraFocus(showFocus && r == targetRacer);
        }

        double targetY = targetRacer.Y;
        double targetOffset = Math.Max(0, targetY * scale - viewportHeight * 0.38);
        double maxOffset = Math.Max(0, TrackHeight * scale - viewportHeight);
        targetOffset = Math.Clamp(targetOffset, 0, maxOffset);

        if (force)
        {
            RaceScrollViewer.ScrollToVerticalOffset(targetOffset);
        }
        else
        {
            double current = RaceScrollViewer.VerticalOffset;
            double alpha = 1.0 - Math.Exp(-8.0 * Math.Max(dt, 0.001));
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

        RaceRacer? targetRacer = null;
        if (_targetCameraRank > 1 || _targetCameraStudentNumber.HasValue)
        {
            var sorted = _racers
                .OrderBy(r => r.IsFinished ? 0 : 1)
                .ThenBy(r => r.IsFinished ? r.FinishRank : 0)
                .ThenByDescending(r => r.Y)
                .ToList();
            if (sorted.Count > 0)
            {
                if (_targetCameraStudentNumber.HasValue)
                {
                    targetRacer = sorted.FirstOrDefault(r => r.Student.Number == _targetCameraStudentNumber.Value);
                }
                else
                {
                    int rankIdx = Math.Clamp(_targetCameraRank - 1, 0, sorted.Count - 1);
                    targetRacer = sorted[rankIdx];
                }
            }
        }

        // Update dots
        foreach (var r in _racers)
        {
            bool isTarget = (r == targetRacer);
            double dotSize = isTarget ? 11 : 7;
            r.MinimapDot.Width = dotSize;
            r.MinimapDot.Height = dotSize;

            if (isTarget)
            {
                r.MinimapDot.Fill = new SolidColorBrush(Color.FromRgb(56, 189, 248)); // Cyan
                r.MinimapDot.Stroke = new SolidColorBrush(Color.FromRgb(254, 240, 138)); // Yellow ring
                r.MinimapDot.StrokeThickness = 2;
                Panel.SetZIndex(r.MinimapDot, 10);
            }
            else
            {
                r.MinimapDot.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047"));
                r.MinimapDot.Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B45309"));
                r.MinimapDot.StrokeThickness = 1;
                Panel.SetZIndex(r.MinimapDot, 1);
            }

            Canvas.SetLeft(r.MinimapDot, r.X * scaleX - dotSize / 2.0);
            Canvas.SetTop(r.MinimapDot, r.Y * scaleY - dotSize / 2.0);
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

        RaceRacer? currentTracked = null;
        if (sorted.Count > 0)
        {
            if (_targetCameraStudentNumber.HasValue)
            {
                currentTracked = sorted.FirstOrDefault(r => r.Student.Number == _targetCameraStudentNumber.Value);
            }
            else if (_targetCameraRank > 1)
            {
                int rankIdx = Math.Clamp(_targetCameraRank - 1, 0, sorted.Count - 1);
                currentTracked = sorted[rankIdx];
            }
            else
            {
                currentTracked = _racers.Where(r => !r.IsFinished).OrderByDescending(r => r.Y).FirstOrDefault() ?? sorted[0];
            }
        }

        for (int i = 0; i < sorted.Count; i++)
        {
            var racer = sorted[i];
            int rank = i + 1;
            bool isTracked = (racer == currentTracked);

            var row = new Border
            {
                Margin = new Thickness(0, 1, 0, 1),
                Height = 32,
                CornerRadius = new CornerRadius(6),
                Background = isTracked
                    ? new SolidColorBrush(Color.FromArgb(50, 56, 189, 248))
                    : Brushes.Transparent,
                BorderBrush = isTracked
                    ? new SolidColorBrush(Color.FromArgb(180, 56, 189, 248))
                    : Brushes.Transparent,
                BorderThickness = new Thickness(isTracked ? 1.5 : 0),
                Cursor = Cursors.Hand,
                ToolTip = $"{rank}등 {racer.Student.Name} (클릭하여 시점 전환)"
            };

            int studentNum = racer.Student.Number;
            row.MouseLeftButtonDown += (s, e) =>
            {
                SetCameraTargetStudent(studentNum);
            };

            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(28) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(22) });

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
            grid.Children.Add(badge);

            // Animal Avatar
            var avatarImg = new Image
            {
                Width = 24,
                Height = 24,
                Source = AnimalAvatarCatalog.GetAvatarBitmap(racer.Student.EffectiveAvatarId),
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            RenderOptions.SetBitmapScalingMode(avatarImg, BitmapScalingMode.HighQuality);
            Grid.SetColumn(avatarImg, 1);
            grid.Children.Add(avatarImg);

            // Student Name
            var nameText = new TextBlock
            {
                Text = racer.Student.Name,
                FontSize = 12,
                FontWeight = (rank <= 3 || isTracked) ? FontWeights.Bold : FontWeights.Normal,
                Foreground = isTracked
                    ? new SolidColorBrush(Color.FromRgb(56, 189, 248))
                    : (rank == 1 ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")) : Brushes.White),
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(6, 0, 0, 0),
                TextTrimming = TextTrimming.CharacterEllipsis
            };
            Grid.SetColumn(nameText, 2);
            grid.Children.Add(nameText);

            // 🎥 Camera Tracking Indicator Icon
            if (isTracked)
            {
                var camIcon = new TextBlock
                {
                    Text = "🎥",
                    FontSize = 11,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center
                };
                Grid.SetColumn(camIcon, 3);
                grid.Children.Add(camIcon);
            }

            row.Child = grid;
            PanelLeaderboard.Children.Add(row);
        }
    }

    #region Camera Viewpoint Control

    private void UpdateCameraRankOptions()
    {
        if (CbCameraRank == null) return;
        CbCameraRank.SelectionChanged -= CbCameraRank_SelectionChanged;
        CbCameraRank.Items.Clear();

        int total = _racers.Count;
        if (total == 0) total = 30;

        CbCameraRank.Items.Add(new ComboBoxItem { Content = "1등 (선두)", Tag = 1 });

        for (int r = 2; r <= total; r++)
        {
            string label = (r == total) ? $"{r}등 (꼴등)" : $"{r}등";
            CbCameraRank.Items.Add(new ComboBoxItem { Content = label, Tag = r });
        }

        SetCameraRank(1, notifyCombo: true);
        CbCameraRank.SelectionChanged += CbCameraRank_SelectionChanged;
    }

    public void SetCameraRank(int rank, bool notifyCombo = true)
    {
        int total = Math.Max(1, _racers.Count);
        _targetCameraRank = Math.Clamp(rank, 1, total);
        _targetCameraStudentNumber = null;

        if (notifyCombo && CbCameraRank != null)
        {
            CbCameraRank.SelectionChanged -= CbCameraRank_SelectionChanged;
            for (int i = 0; i < CbCameraRank.Items.Count; i++)
            {
                if (CbCameraRank.Items[i] is ComboBoxItem item && item.Tag is int r && r == _targetCameraRank)
                {
                    CbCameraRank.SelectedIndex = i;
                    break;
                }
            }
            CbCameraRank.SelectionChanged += CbCameraRank_SelectionChanged;
        }

        if (BtnCameraReset1st != null)
        {
            BtnCameraReset1st.Visibility = (_targetCameraRank == 1) ? Visibility.Collapsed : Visibility.Visible;
        }

        UpdateCameraViewport(0, force: false);
        UpdateLeaderboard();
        UpdateMinimap();
    }

    public void SetCameraTargetStudent(int studentNumber)
    {
        _targetCameraStudentNumber = studentNumber;

        var sorted = _racers
            .OrderBy(r => r.IsFinished ? 0 : 1)
            .ThenBy(r => r.IsFinished ? r.FinishRank : 0)
            .ThenByDescending(r => r.Y)
            .ToList();

        int idx = sorted.FindIndex(r => r.Student.Number == studentNumber);
        if (idx >= 0)
        {
            _targetCameraRank = idx + 1;
            if (CbCameraRank != null)
            {
                CbCameraRank.SelectionChanged -= CbCameraRank_SelectionChanged;
                for (int i = 0; i < CbCameraRank.Items.Count; i++)
                {
                    if (CbCameraRank.Items[i] is ComboBoxItem item && item.Tag is int r && r == _targetCameraRank)
                    {
                        CbCameraRank.SelectedIndex = i;
                        break;
                    }
                }
                CbCameraRank.SelectionChanged += CbCameraRank_SelectionChanged;
            }
        }

        if (BtnCameraReset1st != null)
        {
            BtnCameraReset1st.Visibility = Visibility.Visible;
        }

        UpdateCameraViewport(0, force: false);
        UpdateLeaderboard();
        UpdateMinimap();
    }

    private void BtnCameraPrevRank_Click(object sender, RoutedEventArgs e)
    {
        SetCameraRank(_targetCameraRank - 1);
    }

    private void BtnCameraNextRank_Click(object sender, RoutedEventArgs e)
    {
        SetCameraRank(_targetCameraRank + 1);
    }

    private void BtnCameraReset1st_Click(object sender, RoutedEventArgs e)
    {
        SetCameraRank(1);
    }

    private void CbCameraRank_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CbCameraRank.SelectedItem is ComboBoxItem item && item.Tag is int r)
        {
            SetCameraRank(r, notifyCombo: false);
        }
    }

    #endregion

    private void TriggerWinnerCelebration(StudentItem winner)
    {
        StopBgm();
        if (_soundEnabled)
        {
            _soundService.PlayFanfare();
        }

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

    private void TriggerWaterSplash(double x, double y)
    {
        if (ImgWaterSplash == null) return;
        Canvas.SetLeft(ImgWaterSplash, 270);
        Canvas.SetTop(ImgWaterSplash, Math.Clamp(y - 20, 3320, 3380));
        ImgWaterSplash.Visibility = Visibility.Visible;
        ImgWaterSplash.Opacity = 1.0;

        var anim = new DoubleAnimation(1.0, 0.0, TimeSpan.FromMilliseconds(450))
        {
            BeginTime = TimeSpan.FromMilliseconds(150)
        };
        anim.Completed += (s, e) =>
        {
            ImgWaterSplash.Visibility = Visibility.Collapsed;
        };
        ImgWaterSplash.BeginAnimation(UIElement.OpacityProperty, anim);
    }

#endregion

    #region Window UI Controls

    private void BtnResetToStart_Click(object sender, RoutedEventArgs e)
    {
        ResetToStartLine();
    }

    private void BtnInitAll_Click(object sender, RoutedEventArgs e)
    {
        StopBgm();
        _soundService.StopAll();
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
        _soundService.IsMuted = !_soundEnabled;
        if (!_soundEnabled)
        {
            StopBgm();
            _soundService.StopAll();
        }
        else
        {
            if (_isPlaying && !_isPaused)
            {
                PlayBgm();
            }
        }
        UpdateSoundUi();
    }

    private void SliderSoundVolume_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (TxtSoundVolume == null || _soundService == null) return;
        int vol = (int)Math.Round(SliderSoundVolume.Value);
        TxtSoundVolume.Text = vol == 0 ? "OFF" : $"{vol}%";
        _soundService.MasterVolume = vol / 100.0;
        if (vol == 0)
        {
            _soundEnabled = false;
            _soundService.IsMuted = true;
            StopBgm();
            _soundService.StopAll();
            BtnSoundToggle.Content = "🔇";
            BtnSoundToggle.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            BtnSoundToggle.ToolTip = "레이스 배경음악 켜기 (기본: 음소거)";
        }
        else
        {
            _soundEnabled = true;
            _soundService.IsMuted = false;
            if (_isPlaying && !_isPaused)
            {
                PlayBgm();
            }
            BtnSoundToggle.Content = "🔊";
            BtnSoundToggle.Foreground = new SolidColorBrush(Color.FromRgb(56, 189, 248));
            BtnSoundToggle.ToolTip = "배경음악 음소거하기";
        }
    }

    private void UpdateSoundUi()
    {
        if (BtnSoundToggle == null || SliderSoundVolume == null || TxtSoundVolume == null) return;
        if (_soundEnabled && !_soundService.IsMuted)
        {
            BtnSoundToggle.Content = "🔊";
            BtnSoundToggle.Foreground = new SolidColorBrush(Color.FromRgb(56, 189, 248));
            BtnSoundToggle.ToolTip = "배경음악 음소거하기";
            if (SliderSoundVolume.Value <= 0) SliderSoundVolume.Value = 80;
            TxtSoundVolume.Text = $"{(int)Math.Round(SliderSoundVolume.Value)}%";
            _soundService.MasterVolume = SliderSoundVolume.Value / 100.0;
        }
        else
        {
            BtnSoundToggle.Content = "🔇";
            BtnSoundToggle.Foreground = new SolidColorBrush(Color.FromRgb(239, 68, 68));
            BtnSoundToggle.ToolTip = "레이스 배경음악 켜기 (기본: 음소거)";
            TxtSoundVolume.Text = "OFF";
        }
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

    public void StopAndReset()
    {
        StopBgm();
        _soundService.StopAll();
        _isPlaying = false;
        _isPaused = false;
        _gameTimer?.Stop();
        _finishedCount = 0;
        _winners.Clear();
        if (BorderPausedBanner != null) BorderPausedBanner.Visibility = Visibility.Collapsed;
        if (BtnPauseResume != null) BtnPauseResume.IsEnabled = false;
        if (TxtPauseIcon != null) TxtPauseIcon.Text = "⏸ ";
        if (TxtPauseLabel != null) TxtPauseLabel.Text = "일시정지";
        if (GridCelebration != null)
        {
            GridCelebration.Visibility = Visibility.Collapsed;
        }
        ResetToStartLine();
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        StopAndReset();
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
    public double StuckTimer { get; set; } = 0;

    // Wall-Pinned (표창 솔방울에 꽂혀 벽에 고정된 상태)
    public double PinnedTimer { get; set; } = 0;
    public int PinnedSide { get; set; } = 0; // -1: Left wall, 1: Right wall
    public bool IsBlownByPinecone { get; set; } = false;
    public double PineconePushDir { get; set; } = 0;

    public Grid Visual { get; }
    public Ellipse MinimapDot { get; }
    private readonly RotateTransform _rot;
    private readonly Image _pinnedPineconeImg;
    private readonly Border _dizzyBadge;
    private readonly Border _focusRing;

    public RaceRacer(StudentItem student, double x, double y, double radius)
    {
        Student = student;
        X = x;
        Y = y;
        Radius = radius;

        Visual = new Grid
        {
            Width = 56,
            Height = 58,
            Cursor = Cursors.Hand,
            ToolTip = $"{student.Number}번 {student.Name} (클릭하여 시점 전환)"
        };

        _rot = new RotateTransform(0);
        Visual.RenderTransformOrigin = new Point(0.5, 0.35);
        Visual.RenderTransform = _rot;

        // 0. Camera Focus Ring (카메라 시점 집중 표시)
        _focusRing = new Border
        {
            Width = 46,
            Height = 46,
            CornerRadius = new CornerRadius(23),
            BorderBrush = new SolidColorBrush(Color.FromArgb(240, 56, 189, 248)),
            BorderThickness = new Thickness(2.5),
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(0, -3, 0, 0),
            Visibility = Visibility.Collapsed,
            IsHitTestVisible = false
        };
        _focusRing.Effect = new DropShadowEffect
        {
            Color = Color.FromRgb(56, 189, 248),
            BlurRadius = 12,
            Opacity = 0.9,
            ShadowDepth = 0
        };
        Visual.Children.Add(_focusRing);

        // 1. Natural Animal Avatar (FRAMELESS - No circular frame or thick stroke!)
        var img = new Image
        {
            Width = 40,
            Height = 40,
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

        // 3. Embedded Shuriken Pinecone ("표창처럼 벽에 꽂히는 솔방울")
        _pinnedPineconeImg = new Image
        {
            Width = 34,
            Height = 34,
            Source = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_pinecone_shuriken.png")),
            Visibility = Visibility.Collapsed,
            IsHitTestVisible = false,
            VerticalAlignment = VerticalAlignment.Top,
            RenderTransformOrigin = new Point(0.5, 0.5)
        };
        RenderOptions.SetBitmapScalingMode(_pinnedPineconeImg, BitmapScalingMode.HighQuality);
        _pinnedPineconeImg.Effect = new DropShadowEffect
        {
            Color = Color.FromRgb(245, 158, 11),
            BlurRadius = 8,
            Opacity = 0.85,
            ShadowDepth = 0
        };
        Visual.Children.Add(_pinnedPineconeImg);

        // 4. Dizzy Stars Badge ("💫 머리 위 회전 별")
        _dizzyBadge = new Border
        {
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(0, -18, 0, 0),
            Visibility = Visibility.Collapsed,
            IsHitTestVisible = false
        };
        _dizzyBadge.Child = new TextBlock
        {
            Text = "💫",
            FontSize = 16,
            HorizontalAlignment = HorizontalAlignment.Center
        };
        Visual.Children.Add(_dizzyBadge);

        // 5. Minimap Dot
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

    public void PinToWall(int side, double duration)
    {
        PinnedTimer = duration;
        PinnedSide = side;
        IsBlownByPinecone = false;
        Vx = 0;
        Vy = 0;

        _pinnedPineconeImg.Visibility = Visibility.Visible;
        _dizzyBadge.Visibility = Visibility.Visible;

        if (side < 0)
        {
            // Left wall: shuriken blade firmly pins player into the left wall!
            _pinnedPineconeImg.HorizontalAlignment = HorizontalAlignment.Left;
            _pinnedPineconeImg.Margin = new Thickness(-14, 3, 0, 0);
            _pinnedPineconeImg.RenderTransform = new RotateTransform(-45);
        }
        else
        {
            // Right wall: shuriken blade firmly pins player into the right wall!
            _pinnedPineconeImg.HorizontalAlignment = HorizontalAlignment.Right;
            _pinnedPineconeImg.Margin = new Thickness(0, 3, -14, 0);
            _pinnedPineconeImg.RenderTransform = new RotateTransform(45);
        }
    }

    public void Unpin()
    {
        PinnedTimer = 0;
        IsBlownByPinecone = false;
        _pinnedPineconeImg.Visibility = Visibility.Collapsed;
        _dizzyBadge.Visibility = Visibility.Collapsed;
        _rot.Angle = 0;

        // Pop outward from wall back into race!
        Vx = -PinnedSide * 85.0;
        Vy = 130.0;
    }

    public void UpdateVisual()
    {
        Canvas.SetLeft(Visual, X - Visual.Width / 2.0);
        Canvas.SetTop(Visual, Y - 20.0);

        if (PinnedTimer > 0)
        {
            // Rapid cartoon struggle & quiver animation (trying to pull free from the pinned wall!)
            double wiggle = Math.Sin(PinnedTimer * 42.0) * 14.0;
            _rot.Angle = wiggle;
        }
        else
        {
            // Tilt based on horizontal velocity
            double angle = Math.Clamp(Vx * 0.15, -28.0, 28.0);
            _rot.Angle = angle;
        }
    }

    public void SetCameraFocus(bool focused)
    {
        _focusRing.Visibility = focused ? Visibility.Visible : Visibility.Collapsed;
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

        // Ground shadow for spatial grounding
        var shadow = new Ellipse
        {
            Width = radius * 1.7,
            Height = radius * 0.75,
            Fill = new SolidColorBrush(Color.FromArgb(70, 15, 10, 5)),
            VerticalAlignment = VerticalAlignment.Bottom,
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, -3),
            IsHitTestVisible = false
        };
        Visual.Children.Add(shadow);

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

        // Soft drop shadow rotating underneath the log
        var shadow = new Border
        {
            Width = length * 0.94,
            Height = Visual.Height * 0.75,
            Background = new SolidColorBrush(Color.FromArgb(90, 15, 10, 5)),
            CornerRadius = new CornerRadius(thickness * 0.45),
            Margin = new Thickness(0, 8, 0, 0),
            IsHitTestVisible = false
        };
        Visual.Children.Add(shadow);

        var img = new Image
        {
            Width = length,
            Height = Visual.Height,
            Source = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_log_rotating.png")),
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        Visual.Children.Add(img);

        // Center bronze/gold rivet axle cap
        var rivet = new Ellipse
        {
            Width = 18,
            Height = 18,
            Fill = new SolidColorBrush(Color.FromRgb(245, 158, 11)),
            Stroke = new SolidColorBrush(Color.FromRgb(69, 26, 3)),
            StrokeThickness = 2.5,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            IsHitTestVisible = false
        };
        Visual.Children.Add(rivet);

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
        double halfT = Thickness * 0.32;

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
                r.Vy = Math.Max(logVy + newRelVy + 25, 45.0);
            }
            return true;
        }
        return false;
    }
}

public class PoppableBubble
{
    public double X { get; }
    public double Y { get; }
    public double Radius { get; }
    public bool IsPopped { get; private set; }
    public Grid Visual { get; }

    private readonly ScaleTransform _scale;
    private readonly double _floatPhase;

    public PoppableBubble(double x, double y, double radius)
    {
        X = x;
        Y = y;
        Radius = radius;
        _floatPhase = (x * 0.04) % (Math.PI * 2);

        Visual = new Grid
        {
            Width = radius * 2,
            Height = radius * 2,
            RenderTransformOrigin = new Point(0.5, 0.5)
        };

        _scale = new ScaleTransform(1, 1);
        Visual.RenderTransform = _scale;

        var img = new Image
        {
            Width = radius * 2,
            Height = radius * 2,
            Source = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_bubble.png")),
            IsHitTestVisible = false
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        Visual.Children.Add(img);

        Canvas.SetLeft(Visual, X - radius);
        Canvas.SetTop(Visual, Y - radius);
    }

    public void Update(double totalSeconds)
    {
        if (IsPopped) return;
        // Gentle bobbing motion
        double bob = Math.Sin(totalSeconds * 2.8 + _floatPhase) * 3.5;
        Canvas.SetTop(Visual, (Y + bob) - Radius);
    }

    public void Pop()
    {
        if (IsPopped) return;
        IsPopped = true;

        // Visual pop effect: rapid expansion & fade out
        var scaleAnim = new DoubleAnimation(1.0, 1.45, TimeSpan.FromMilliseconds(130));
        var opacityAnim = new DoubleAnimation(1.0, 0.0, TimeSpan.FromMilliseconds(130));
        opacityAnim.Completed += (s, e) =>
        {
            Visual.Visibility = Visibility.Collapsed;
        };

        _scale.BeginAnimation(ScaleTransform.ScaleXProperty, scaleAnim);
        _scale.BeginAnimation(ScaleTransform.ScaleYProperty, scaleAnim);
        Visual.BeginAnimation(UIElement.OpacityProperty, opacityAnim);
    }

    public void Reset()
    {
        IsPopped = false;
        Visual.Visibility = Visibility.Visible;
        Visual.Opacity = 1.0;
        _scale.BeginAnimation(ScaleTransform.ScaleXProperty, null);
        _scale.BeginAnimation(ScaleTransform.ScaleYProperty, null);
        Visual.BeginAnimation(UIElement.OpacityProperty, null);
        _scale.ScaleX = 1.0;
        _scale.ScaleY = 1.0;
        Canvas.SetLeft(Visual, X - Radius);
        Canvas.SetTop(Visual, Y - Radius);
    }
}

public class PopOutSquirrel
{
    public double X { get; }
    public double Y { get; }
    public double CurrentX => X;
    public double CurrentY => Y;
    public double Radius { get; }
    public bool IsFacingRight { get; }
    public bool IsActive => true;

    public Grid BranchVisual { get; }
    public Grid TreeHoleVisual => BranchVisual; // Backwards-compatible alias
    public Grid SquirrelVisual { get; }

    public string ProjectileAsset { get; }
    public Action<ThrownProjectile>? OnThrowProjectile { get; set; }

    private readonly ScaleTransform _scale;
    private readonly Image _sqImg;
    private readonly BitmapImage _frameIdle;
    private readonly BitmapImage _frameWindup;
    private readonly BitmapImage _frameThrow;
    private readonly BitmapImage _frameCheer;

    private readonly double _startDelay;
    private double _stateTimer;
    private int _state; // 0=Idle, 1=Windup, 2=Throw, 3=Cheer
    private double _bumpTimer;
    private double _idleAnimTime;
    private bool _hasThrownThisCycle;

    // Snappy, rapid-fire barrage throw cycle (~1.3s total)
    private const double DurationIdle = 0.85;
    private const double DurationWindup = 0.16;
    private const double DurationThrow = 0.14;
    private const double DurationCheer = 0.20;

    public PopOutSquirrel(double x, double y, double radius, bool isFacingRight, double startDelay, string projectileAsset)
    {
        X = x;
        Y = y;
        Radius = radius;
        IsFacingRight = isFacingRight;
        _startDelay = startDelay;
        ProjectileAsset = projectileAsset;

        _state = 0;
        _stateTimer = -startDelay;

        // Load 2D side-profile animated sprite frames (all 512x512, transparent, facing right)
        _frameIdle = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_squirrel_idle.png"));
        _frameWindup = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_squirrel_windup.png"));
        _frameThrow = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_squirrel_throw.png"));
        _frameCheer = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_squirrel_cheer.png"));

        // 1. Wooden Branch Perch Visual (Cliff side footing)
        double branchW = 92;
        double branchH = 50;
        BranchVisual = new Grid
        {
            Width = branchW,
            Height = branchH,
            IsHitTestVisible = false
        };
        var branchImg = new Image
        {
            Width = branchW,
            Height = branchH,
            Source = new BitmapImage(new Uri("pack://application:,,,/assets/race/cartoon_branch_perch.png"))
        };
        RenderOptions.SetBitmapScalingMode(branchImg, BitmapScalingMode.HighQuality);
        BranchVisual.Children.Add(branchImg);

        if (isFacingRight)
        {
            Canvas.SetLeft(BranchVisual, Math.Max(0, X - 35));
            Canvas.SetTop(BranchVisual, y + 14);
        }
        else
        {
            BranchVisual.RenderTransformOrigin = new Point(0.5, 0.5);
            BranchVisual.RenderTransform = new ScaleTransform(-1.0, 1.0);
            Canvas.SetLeft(BranchVisual, Math.Min(680 - branchW, X - branchW + 35));
            Canvas.SetTop(BranchVisual, y + 14);
        }

        // 2. Animated Squirrel Visual (Stationed on branch, always visible!)
        double sqSize = 84;
        SquirrelVisual = new Grid
        {
            Width = sqSize,
            Height = sqSize,
            RenderTransformOrigin = new Point(0.5, 0.88),
            IsHitTestVisible = false,
            Opacity = 1.0
        };

        _scale = new ScaleTransform(isFacingRight ? 1.0 : -1.0, 1.0);
        SquirrelVisual.RenderTransform = _scale;

        _sqImg = new Image
        {
            Width = sqSize,
            Height = sqSize,
            Source = _frameIdle
        };
        RenderOptions.SetBitmapScalingMode(_sqImg, BitmapScalingMode.HighQuality);
        SquirrelVisual.Children.Add(_sqImg);

        Canvas.SetLeft(SquirrelVisual, X - sqSize / 2.0);
        Canvas.SetTop(SquirrelVisual, Y - sqSize / 2.0);
    }

    public void Bump()
    {
        _bumpTimer = 0.25;
        _scale.ScaleX = (IsFacingRight ? 1.0 : -1.0) * 1.35;
        _scale.ScaleY = 1.35;
    }

    public void Update(double dt, bool hasTargetApproaching)
    {
        if (_bumpTimer > 0)
        {
            _bumpTimer -= dt;
            if (_bumpTimer <= 0)
            {
                _scale.ScaleX = IsFacingRight ? 1.0 : -1.0;
                _scale.ScaleY = 1.0;
            }
        }

        _stateTimer += dt;
        _idleAnimTime += dt;

        switch (_state)
        {
            case 0: // Idle (holding pinecone, breathing gently)
                if (_sqImg.Source != _frameIdle) _sqImg.Source = _frameIdle;
                _hasThrownThisCycle = false;

                if (_bumpTimer <= 0)
                {
                    _scale.ScaleY = 1.0 + 0.03 * Math.Sin(_idleAnimTime * 4.0);
                }

                // Only start windup/throw cycle if delay has elapsed AND a racer is approaching!
                if (_stateTimer >= DurationIdle && hasTargetApproaching)
                {
                    _state = 1; // Quick Windup!
                    _stateTimer = 0;
                    _sqImg.Source = _frameWindup;
                    // Lean back anticipation
                    _scale.ScaleX = (IsFacingRight ? 1.0 : -1.0) * 0.92;
                    _scale.ScaleY = 1.06;
                }
                break;

            case 1: // Windup anticipation (cocked back, determined eye)
                if (_sqImg.Source != _frameWindup) _sqImg.Source = _frameWindup;

                if (_stateTimer >= DurationWindup)
                {
                    _state = 2; // Snap Throw!
                    _stateTimer = 0;
                    _sqImg.Source = _frameThrow;
                    // Dynamic forward squash-and-stretch
                    _scale.ScaleX = (IsFacingRight ? 1.0 : -1.0) * 1.15;
                    _scale.ScaleY = 0.94;

                    // Release high-speed pinecone shuriken projectile right from outstretched paw!
                    if (!_hasThrownThisCycle)
                    {
                        _hasThrownThisCycle = true;
                        double throwX = IsFacingRight ? (X + 42) : (X - 42);
                        double throwY = Y - 2;
                        // Razor-sharp horizontal ninja shuriken throw across track (780 px/s)!
                        double vx = (IsFacingRight ? 1.0 : -1.0) * 780.0;
                        double vy = 0.0;
                        OnThrowProjectile?.Invoke(new ThrownProjectile(throwX, throwY, vx, vy, ProjectileAsset));
                    }
                }
                break;

            case 2: // Throw follow-through
                if (_sqImg.Source != _frameThrow) _sqImg.Source = _frameThrow;

                if (_stateTimer >= DurationThrow)
                {
                    _state = 3; // Joyful cheer/chuckle
                    _stateTimer = 0;
                    _sqImg.Source = _frameCheer;
                    _scale.ScaleX = (IsFacingRight ? 1.0 : -1.0) * 1.08;
                    _scale.ScaleY = 1.08;
                }
                break;

            case 3: // Cheer & chuckle
                if (_sqImg.Source != _frameCheer) _sqImg.Source = _frameCheer;

                if (_stateTimer >= DurationCheer)
                {
                    _state = 0; // Back to Idle for next rapid throw!
                    _stateTimer = 0;
                    _sqImg.Source = _frameIdle;
                    _scale.ScaleX = IsFacingRight ? 1.0 : -1.0;
                    _scale.ScaleY = 1.0;
                }
                break;
        }
    }

    public void Reset()
    {
        _state = 0;
        _stateTimer = -_startDelay;
        _idleAnimTime = 0;
        _bumpTimer = 0;
        _hasThrownThisCycle = false;
        _sqImg.Source = _frameIdle;
        _scale.ScaleX = IsFacingRight ? 1.0 : -1.0;
        _scale.ScaleY = 1.0;
        SquirrelVisual.Opacity = 1.0;
    }
}

public class ThrownProjectile
{
    public double X { get; set; }
    public double Y { get; set; }
    public double Vx { get; set; }
    public double Vy { get; set; }
    public double Radius { get; } = 18;
    public bool IsDestroyed { get; private set; }
    public Grid Visual { get; }
    private readonly RotateTransform _rot;
    private double _angle;
    private double _lifeTimer;
    private const double MaxLife = 3.2;

    public ThrownProjectile(double x, double y, double vx, double vy, string assetName)
    {
        X = x;
        Y = y;
        Vx = vx;
        Vy = vy;

        double size = 42;
        bool movingRight = vx > 0;

        Visual = new Grid
        {
            Width = size + 44, // Extra width for motion speed trail
            Height = size,
            RenderTransformOrigin = new Point(0.5, 0.5),
            IsHitTestVisible = false
        };

        // 1. Wind Slash / Speed Trail (공기를 가르는 잔상 스피드라인)
        var speedTrail = new Border
        {
            Width = 38,
            Height = 6,
            CornerRadius = new CornerRadius(3),
            Background = new LinearGradientBrush(
                movingRight
                    ? Color.FromArgb(160, 254, 240, 138)
                    : Color.FromArgb(0, 254, 240, 138),
                movingRight
                    ? Color.FromArgb(0, 254, 240, 138)
                    : Color.FromArgb(160, 254, 240, 138),
                new Point(movingRight ? 1 : 0, 0.5),
                new Point(movingRight ? 0 : 1, 0.5)),
            HorizontalAlignment = movingRight ? HorizontalAlignment.Left : HorizontalAlignment.Right,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(movingRight ? 4 : 0, 0, movingRight ? 0 : 4, 0),
            IsHitTestVisible = false
        };
        Visual.Children.Add(speedTrail);

        // 2. Rotating 4-Pointed Pinecone Shuriken Star
        var shurikenGrid = new Grid
        {
            Width = size,
            Height = size,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            RenderTransformOrigin = new Point(0.5, 0.5)
        };
        _rot = new RotateTransform(0);
        shurikenGrid.RenderTransform = _rot;

        var img = new Image
        {
            Width = size,
            Height = size,
            Source = new BitmapImage(new Uri($"pack://application:,,,/assets/race/{assetName}")),
        };
        RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
        shurikenGrid.Children.Add(img);

        shurikenGrid.Effect = new DropShadowEffect
        {
            Color = Color.FromRgb(245, 158, 11), // Golden amber glow
            BlurRadius = 8,
            Opacity = 0.85,
            ShadowDepth = 0
        };

        Visual.Children.Add(shurikenGrid);

        Canvas.SetLeft(Visual, X - Visual.Width / 2.0);
        Canvas.SetTop(Visual, Y - Visual.Height / 2.0);
    }

    public void Update(double dt)
    {
        if (IsDestroyed) return;

        _lifeTimer += dt;
        if (_lifeTimer >= MaxLife || Y > 3450)
        {
            Destroy();
            return;
        }

        // Razor-sharp horizontal shuriken flight across track
        X += Vx * dt;
        Y += Vy * dt;

        // Embedding / Impact against far track walls:
        StudentPickerWindow.GetTrackBoundaries(Y, out double pLeft, out double pRight);
        if (Vx > 0 && X + Radius >= pRight)
        {
            // Shuriken embeds into far right wall and vanishes with thunk
            Destroy();
            return;
        }
        else if (Vx < 0 && X - Radius <= pLeft)
        {
            // Shuriken embeds into far left wall and vanishes with thunk
            Destroy();
            return;
        }

        // High-speed whirling ninja spin (1440 deg/s = 4 full rotations per second!)
        _angle += Math.Sign(Vx) * dt * 1440.0;
        _rot.Angle = _angle;

        Canvas.SetLeft(Visual, X - Visual.Width / 2.0);
        Canvas.SetTop(Visual, Y - Visual.Height / 2.0);
    }

    public void Destroy()
    {
        if (IsDestroyed) return;
        IsDestroyed = true;
        Visual.Visibility = Visibility.Collapsed;
    }
}

#endregion

