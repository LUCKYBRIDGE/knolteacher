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

    // Physics Simulation State
    private readonly List<PinballBall> _balls = new();
    private readonly List<PinballPeg> _pegs = new();
    private readonly List<PinballBumper> _bumpers = new();
    private readonly List<PinballRail> _rails = new();
    private readonly List<ConfettiParticle> _confetti = new();

    private DispatcherTimer? _gameTimer;
    private DispatcherTimer? _classicShuffleTimer;
    private int _classicShuffleCount = 0;
    private StudentItem? _classicFinalPicked;

    private bool _isPlaying = false;
    private bool _soundEnabled = true;
    private StudentItem? _lastWinner = null;
    private DateTime _lastFrameTime = DateTime.UtcNow;

    // Responsive camera state for the tall 680x1120 forest course.
    private const double PinballMapWidth = 680.0;
    private const double PinballMapHeight = 1120.0;
    private const double PinballGoalY = 1038.0;
    private const double CameraVisibleWorldHeight = 620.0;
    private double _cameraOffsetY = 0;
    private double _cameraScale = 1;
    private PinballBall? _cameraLeader;

    public StudentPickerWindow(IStudentManagerService studentService, ISoundService soundService, IDisplayManager? displayManager = null)
    {
        _studentService = studentService;
        _soundService = soundService;
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        InitializeComponent();

        Loaded += (s, e) =>
        {
            SetupPegsAndBumpers();
            UpdateStatus();
            PositionToDefaultMonitor();
            UpdateCameraAndLeader(0, force: true);
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
            BtnSwitchMonitor.Content = _currentMonitorIndex == 1 ? "📺 모니터 2 (학생용)" : "💻 모니터 1 (메인)";
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
            else
            {
                BtnLaunch_Click(this, new RoutedEventArgs());
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

    private void UpdateStatus()
    {
        int total = _studentService.Students.Count;
        int picked = _studentService.PickedStudentNumbers.Count;
        int remaining = Math.Max(0, total - picked);
        TxtStatus.Text = $"남은 학생: {remaining}명 / 총 {total}명";
        TxtClassicRemaining.Text = $"남은 학생: {remaining}명 / 총 {total}명";
    }

    #region Responsive Race Camera

    private void PinballViewport_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        UpdateCameraAndLeader(0, force: true);
    }

    private void ResetRaceCamera()
    {
        if (_cameraLeader != null)
        {
            _cameraLeader.SetLeader(false);
            _cameraLeader = null;
        }

        _cameraOffsetY = 0;
        RaceProgress.Value = 0;
        TxtRaceLeader.Text = "선두: 출발 대기";
        TxtRaceZone.Text = "🌲 숲속 출발 나무집";
        UpdateCameraAndLeader(0, force: true);
    }

    private void UpdateCameraAndLeader(double dt, bool force = false)
    {
        if (PinballViewport == null || PinballWorldTransform == null) return;

        double viewportWidth = PinballViewport.ActualWidth;
        double viewportHeight = PinballViewport.ActualHeight;
        if (viewportWidth <= 1 || viewportHeight <= 1) return;

        // Fit the full course width whenever possible, but guarantee enough vertical
        // context to see the leader plus the obstacles immediately ahead.
        double widthScale = viewportWidth / PinballMapWidth;
        double contextScale = viewportHeight / CameraVisibleWorldHeight;
        _cameraScale = Math.Max(0.1, Math.Min(widthScale, contextScale));

        PinballBall? leader = null;
        if (_lastWinner != null)
        {
            leader = _balls.FirstOrDefault(b => b.Student.Number == _lastWinner.Number);
        }

        leader ??= _balls
            .Where(b => !b.IsSettled)
            .OrderByDescending(b => b.Y)
            .FirstOrDefault();

        leader ??= _balls
            .OrderByDescending(b => b.Y)
            .FirstOrDefault();

        if (!ReferenceEquals(_cameraLeader, leader))
        {
            _cameraLeader?.SetLeader(false);
            _cameraLeader = leader;
            _cameraLeader?.SetLeader(true);
        }

        double scaledWorldHeight = PinballMapHeight * _cameraScale;
        double targetOffsetY;

        if (scaledWorldHeight <= viewportHeight)
        {
            targetOffsetY = (viewportHeight - scaledWorldHeight) / 2.0;
        }
        else if (leader == null)
        {
            targetOffsetY = 0;
        }
        else
        {
            // Keep the current first-place animal around the upper 38% of the
            // viewport. This leaves more screen below it for upcoming obstacles.
            double leaderScreenAnchor = viewportHeight * 0.38;
            targetOffsetY = leaderScreenAnchor - leader.Y * _cameraScale;
            double minimumOffset = viewportHeight - scaledWorldHeight;
            targetOffsetY = Math.Clamp(targetOffsetY, minimumOffset, 0);
        }

        if (force)
        {
            _cameraOffsetY = targetOffsetY;
        }
        else
        {
            // Exponential smoothing avoids visible camera snaps when the lead changes.
            double alpha = 1.0 - Math.Exp(-6.5 * Math.Max(dt, 0.001));
            _cameraOffsetY += (targetOffsetY - _cameraOffsetY) * alpha;
        }

        double offsetX = (viewportWidth - PinballMapWidth * _cameraScale) / 2.0;
        PinballWorldTransform.Matrix = new Matrix(
            _cameraScale, 0,
            0, _cameraScale,
            offsetX, _cameraOffsetY);

        if (leader != null)
        {
            double progress = Math.Clamp((leader.Y - 60.0) / (PinballGoalY - 60.0) * 100.0, 0, 100);
            RaceProgress.Value = progress;
            TxtRaceLeader.Text = $"선두: {leader.Student.Number}번 {leader.Student.Name} ({leader.Student.AvatarName})";
            TxtRaceZone.Text = GetRaceZoneLabel(leader.Y);
        }
        else
        {
            RaceProgress.Value = 0;
            TxtRaceLeader.Text = "선두: 출발 대기";
            TxtRaceZone.Text = "🌲 숲속 출발 나무집";
        }
    }

    private static string GetRaceZoneLabel(double y)
    {
        if (y < 170) return "🌲 출발 나무집";
        if (y < 330) return "🌰 ① 도토리 갈림길";
        if (y < 530) return "🍄 ② 버섯 숲";
        if (y < 750) return "🪵 ③ 쓰러진 통나무 길";
        if (y < 900) return "💧 ④ 돌개울 징검다리";
        if (y < 1020) return "🌱 ⑤ 뿌리 미로";
        return "🏕️ 숲속 캠프 골인 구간";
    }

    #endregion

    #region Physics Field Setup

    private void SetupPegsAndBumpers()
    {
        // Rebuild only dynamic collision scenery. Static forest art stays in XAML.
        foreach (var peg in _pegs)
        {
            PinballCanvas.Children.Remove(peg.GlowRing);
            PinballCanvas.Children.Remove(peg.Visual);
        }
        foreach (var bumper in _bumpers)
        {
            PinballCanvas.Children.Remove(bumper.Visual);
        }
        foreach (var rail in _rails)
        {
            PinballCanvas.Children.Remove(rail.Visual);
        }

        _pegs.Clear();
        _bumpers.Clear();
        _rails.Clear();

        // 1) Acorn fork: deliberately irregular instead of a pachinko matrix.
        var pegLayout = new (double X, double Y, double R)[]
        {
            (250, 205, 8), (340, 190, 8), (430, 215, 8),
            (185, 265, 8), (295, 275, 8), (390, 270, 8), (505, 275, 8),
            (265, 405, 7), (415, 420, 7),
            (155, 485, 7), (340, 510, 8), (525, 485, 7),
            (225, 865, 8), (455, 870, 8)
        };

        foreach (var p in pegLayout)
        {
            var peg = new PinballPeg(p.X, p.Y, p.R);
            _pegs.Add(peg);
            PinballCanvas.Children.Add(peg.GlowRing);
            PinballCanvas.Children.Add(peg.Visual);
        }

        // 2) Mushroom grove + creek stones: round obstacles create different rebounds.
        _bumpers.Add(new PinballBumper(205, 350, 29, "#C95252", "🍄"));
        _bumpers.Add(new PinballBumper(475, 365, 29, "#D66A4D", "🍄"));
        _bumpers.Add(new PinballBumper(340, 445, 34, "#9D5BA8", "🍄"));

        _bumpers.Add(new PinballBumper(165, 785, 24, "#64786B", "●"));
        _bumpers.Add(new PinballBumper(335, 820, 27, "#71857A", "●"));
        _bumpers.Add(new PinballBumper(510, 785, 24, "#64786B", "●"));

        foreach (var bumper in _bumpers)
        {
            PinballCanvas.Children.Add(bumper.Visual);
        }

        // 3) Fallen logs and roots: long angled shots inspired by pinball ramps/orbits
        // and outdoor forest marble runs. They interrupt the route without sealing it.
        _rails.Add(new PinballRail(92, 545, 292, 598, 12, "#82562F", "통나무"));
        _rails.Add(new PinballRail(588, 610, 390, 665, 12, "#77502D", "통나무"));
        _rails.Add(new PinballRail(105, 685, 286, 728, 10, "#93643A", "나뭇가지"));
        _rails.Add(new PinballRail(575, 700, 450, 738, 9, "#896039", "나뭇가지"));

        // Lower root maze. The last pair works like pinball inlanes and gently
        // channels racers toward the central camp goal.
        _rails.Add(new PinballRail(76, 900, 250, 958, 11, "#684328", "뿌리"));
        _rails.Add(new PinballRail(604, 900, 430, 958, 11, "#684328", "뿌리"));
        _rails.Add(new PinballRail(245, 965, 302, 1018, 10, "#795032", "뿌리"));
        _rails.Add(new PinballRail(435, 965, 378, 1018, 10, "#795032", "뿌리"));

        foreach (var rail in _rails)
        {
            PinballCanvas.Children.Add(rail.Visual);
        }
    }

    #endregion

    #region Launch & Physics Loop

    private void BtnLaunch_Click(object sender, RoutedEventArgs e)
    {
        if (RbModeClassic.IsChecked == true)
        {
            StartClassicRoulette();
            return;
        }

        StartPinballSimulation();
    }

    private void StartPinballSimulation()
    {
        if (_isPlaying) return;

        // Clear existing balls & confetti
        foreach (var b in _balls)
        {
            PinballCanvas.Children.Remove(b.Visual);
        }
        _balls.Clear();

        foreach (var c in _confetti)
        {
            PinballCanvas.Children.Remove(c.Visual);
        }
        _confetti.Clear();

        bool exclude = ChkExcludePicked.IsChecked == true;
        var eligible = exclude
            ? _studentService.Students.Where(s => !_studentService.PickedStudentNumbers.Contains(s.Number)).ToList()
            : _studentService.Students.ToList();

        if (eligible.Count == 0)
        {
            MessageBox.Show("추첨 가능한 학생이 없습니다. 제외 목록을 초기화해주세요.", "안내", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        List<StudentItem> toDrop = new();
        if (RbModeRace.IsChecked == true)
        {
            // Drop ALL eligible students in a chaotic grand race!
            toDrop.AddRange(eligible);
        }
        else
        {
            // Drop 1 random student
            var one = _studentService.PickRandom(exclude);
            if (one != null) toDrop.Add(one);
        }

        var rand = new Random();
        int count = toDrop.Count;
        double spawnWidth = 280;
        double startX = 195;

        for (int i = 0; i < count; i++)
        {
            var student = toDrop[i];
            double x = startX + (i % 7) * (spawnWidth / 6.0) + (rand.NextDouble() * 8 - 4);
            double y = 52 - (i / 7) * 50; // stacked inside/above the tree-house gate
            double vx = (rand.NextDouble() - 0.5) * 60;
            double vy = 40 + rand.NextDouble() * 80;

            var ball = new PinballBall(student, x, y, 21)
            {
                Vx = vx,
                Vy = vy
            };

            _balls.Add(ball);
            PinballCanvas.Children.Add(ball.Visual);
        }

        _isPlaying = true;
        BtnLaunch.IsEnabled = false;
        ResetRaceCamera();
        TxtBtnLaunchLabel.Text = "동물들이 숲길을 달리는 중...";
        _lastWinner = null;
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
        double dt = (now - _lastFrameTime).TotalSeconds;
        _lastFrameTime = now;
        if (dt > 0.05) dt = 0.05; // clamp delta time for stability

        double gravity = 710; // slightly calmer for the taller forest course
        double damp = 0.993;
        var rand = new Random();

        // Update Peg flashes
        foreach (var peg in _pegs)
        {
            peg.Update(dt);
        }
        foreach (var b in _bumpers)
        {
            b.Update(dt);
        }
        foreach (var rail in _rails)
        {
            rail.Update(dt);
        }

        // Update Balls
        for (int i = 0; i < _balls.Count; i++)
        {
            var b = _balls[i];
            if (b.IsSettled) continue;

            b.Vy += gravity * dt;
            b.Vx *= damp;
            b.Vy *= damp;

            b.X += b.Vx * dt;
            b.Y += b.Vy * dt;

            // 1. Boundary Collisions (Walls)
            double leftWall = 38;
            double rightWall = 642;
            if (b.X - b.Radius < leftWall)
            {
                b.X = leftWall + b.Radius;
                b.Vx = Math.Abs(b.Vx) * 0.7 + rand.NextDouble() * 20;
            }
            else if (b.X + b.Radius > rightWall)
            {
                b.X = rightWall - b.Radius;
                b.Vx = -Math.Abs(b.Vx) * 0.7 - rand.NextDouble() * 20;
            }

            // Tree-house exit guides: a short upper funnel only.
            if (b.Y < 165)
            {
                double leftGuide = 120 + Math.Max(0, 165 - b.Y) * 0.38;
                double rightGuide = 560 - Math.Max(0, 165 - b.Y) * 0.38;
                if (b.X - b.Radius < leftGuide)
                {
                    b.X = leftGuide + b.Radius;
                    b.Vx = Math.Abs(b.Vx) * 0.78 + 22;
                }
                if (b.X + b.Radius > rightGuide)
                {
                    b.X = rightGuide - b.Radius;
                    b.Vx = -Math.Abs(b.Vx) * 0.78 - 22;
                }
            }

            // 2. Peg Collisions
            foreach (var peg in _pegs)
            {
                double dx = b.X - peg.X;
                double dy = b.Y - peg.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = b.Radius + peg.Radius;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;

                    b.X += nx * overlap;
                    b.Y += ny * overlap;

                    // Elastic impulse
                    double dot = b.Vx * nx + b.Vy * ny;
                    if (dot < 0)
                    {
                        double restitution = 0.72;
                        b.Vx -= (1 + restitution) * dot * nx + (rand.NextDouble() - 0.5) * 20;
                        b.Vy -= (1 + restitution) * dot * ny;
                        peg.Flash();
                    }
                }
            }

            // 3. Bumper Collisions
            foreach (var bumper in _bumpers)
            {
                double dx = b.X - bumper.X;
                double dy = b.Y - bumper.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = b.Radius + bumper.Radius;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;

                    b.X += nx * overlap;
                    b.Y += ny * overlap;

                    double dot = b.Vx * nx + b.Vy * ny;
                    if (dot < 0)
                    {
                        double bumperBoost = 1.35; // extra bouncy!
                        b.Vx = (-dot * nx * bumperBoost) + (rand.NextDouble() - 0.5) * 40;
                        b.Vy = (-dot * ny * bumperBoost) - 80;
                        bumper.Flash();
                        if (_soundEnabled) _soundService.PlayBeep();
                    }
                }
            }

            // 3.5 Log / branch / root rail collisions
            foreach (var rail in _rails)
            {
                double sx = rail.X2 - rail.X1;
                double sy = rail.Y2 - rail.Y1;
                double lenSq = sx * sx + sy * sy;
                if (lenSq < 0.001) continue;

                double t = ((b.X - rail.X1) * sx + (b.Y - rail.Y1) * sy) / lenSq;
                t = Math.Clamp(t, 0, 1);
                double cx = rail.X1 + t * sx;
                double cy = rail.Y1 + t * sy;
                double dx = b.X - cx;
                double dy = b.Y - cy;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = b.Radius + rail.HalfThickness;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;
                    b.X += nx * overlap;
                    b.Y += ny * overlap;

                    double dot = b.Vx * nx + b.Vy * ny;
                    if (dot < 0)
                    {
                        b.Vx -= (1 + rail.Restitution) * dot * nx;
                        b.Vy -= (1 + rail.Restitution) * dot * ny;
                        // A small tangent nudge avoids balls sticking to long logs.
                        double tx = -ny;
                        double ty = nx;
                        double tangentKick = (rand.NextDouble() - 0.5) * 24;
                        b.Vx += tx * tangentKick;
                        b.Vy += ty * tangentKick;
                        rail.Flash();
                    }
                }
            }

            // 4. Ball-to-Ball Collisions
            for (int j = i + 1; j < _balls.Count; j++)
            {
                var o = _balls[j];
                if (o.IsSettled) continue;

                double dx = o.X - b.X;
                double dy = o.Y - b.Y;
                double dist = Math.Sqrt(dx * dx + dy * dy);
                double minDist = b.Radius + o.Radius;

                if (dist < minDist && dist > 0.001)
                {
                    double nx = dx / dist;
                    double ny = dy / dist;
                    double overlap = minDist - dist;

                    b.X -= nx * overlap * 0.5;
                    b.Y -= ny * overlap * 0.5;
                    o.X += nx * overlap * 0.5;
                    o.Y += ny * overlap * 0.5;

                    double kx = b.Vx - o.Vx;
                    double ky = b.Vy - o.Vy;
                    double p = 2 * (nx * kx + ny * ky) / (2.0); // equal mass

                    b.Vx -= p * nx * 0.7;
                    b.Vy -= p * ny * 0.7;
                    o.Vx += p * nx * 0.7;
                    o.Vy += p * ny * 0.7;
                }
            }

            // 5. Forest camp goal detection
            if (b.Y + b.Radius >= 1038 && b.X >= 255 && b.X <= 425)
            {
                b.IsSettled = true;
                b.Vx = 0;
                b.Vy = 0;
                b.Y = 1065;

                if (_lastWinner == null)
                {
                    _lastWinner = b.Student;
                    TriggerWinnerCelebration(b.Student);
                }
            }
            else if (b.Y > 1085)
            {
                // Side clearing: completed the run, but not first through the camp gate.
                b.IsSettled = true;
                b.Vx = 0;
                b.Vy = 0;
                b.Y = 1070;
            }

            b.UpdateVisual();
        }

        // Camera follows the live leader after every physics step.
        UpdateCameraAndLeader(dt);

        // Update Confetti
        for (int i = _confetti.Count - 1; i >= 0; i--)
        {
            var p = _confetti[i];
            p.Update(dt);
            if (p.IsDead)
            {
                PinballCanvas.Children.Remove(p.Visual);
                _confetti.RemoveAt(i);
            }
        }

        // Check if all balls settled without winner
        if (_balls.Count > 0 && _balls.All(b => b.IsSettled))
        {
            if (_lastWinner == null && _balls.Count > 0)
            {
                // Closest to champion cup wins
                var fallbackWinner = _balls.OrderBy(b => Math.Abs(b.X - 340)).First().Student;
                TriggerWinnerCelebration(fallbackWinner);
            }
            _gameTimer?.Stop();
            _isPlaying = false;
            BtnLaunch.IsEnabled = true;
            TxtBtnLaunchLabel.Text = "동물 숲길 레이스 출발!";
        }
    }

    private void TriggerWinnerCelebration(StudentItem winner)
    {
        _studentService.PickedStudentNumbers.Add(winner.Number);
        UpdateStatus();

        if (_soundEnabled)
        {
            _soundService.PlayChime();
        }

        // Spawn Confetti Particles
        SpawnConfetti(340, 1040, 75);

        // Display Winner Card
        TxtWinnerTitle.Text = $"{winner.Number}번 {winner.Name} ({winner.AvatarName})";
        try
        {
            ImgWinnerAvatar.Source = new BitmapImage(new Uri(winner.AvatarUri, UriKind.RelativeOrAbsolute));
        }
        catch { }

        GridCelebration.Visibility = Visibility.Visible;
    }

    private void SpawnConfetti(double cx, double cy, int count)
    {
        var rand = new Random();
        var colors = new[] { "#FDE047", "#38BDF8", "#EC4899", "#10B981", "#A855F7", "#F97316" };

        for (int i = 0; i < count; i++)
        {
            double angle = rand.NextDouble() * Math.PI * 2;
            double speed = 150 + rand.NextDouble() * 500;
            double vx = Math.Cos(angle) * speed;
            double vy = Math.Sin(angle) * speed - 120;
            string color = colors[rand.Next(colors.Length)];

            var p = new ConfettiParticle(cx, cy, vx, vy, color);
            _confetti.Add(p);
            PinballCanvas.Children.Add(p.Visual);
        }
    }

    private void DismissCelebration()
    {
        GridCelebration.Visibility = Visibility.Collapsed;
        _isPlaying = false;
        BtnLaunch.IsEnabled = true;
        TxtBtnLaunchLabel.Text = "동물 숲길 레이스 출발!";
    }

    private void BtnDismissCelebration_Click(object sender, RoutedEventArgs e) => DismissCelebration();

    private void BtnNextLaunch_Click(object sender, RoutedEventArgs e)
    {
        DismissCelebration();
        StartPinballSimulation();
    }

    #endregion

    #region Classic Roulette Mode

    private void Mode_Checked(object sender, RoutedEventArgs e)
    {
        if (GridClassicMode == null) return;

        if (RbModeClassic.IsChecked == true)
        {
            GridClassicMode.Visibility = Visibility.Visible;
            TxtBtnLaunchLabel.Text = "🎲 발표자 룰렛 뽑기!";
        }
        else
        {
            GridClassicMode.Visibility = Visibility.Collapsed;
            TxtBtnLaunchLabel.Text = "🚀 핀볼 일제 발사! (추첨)";
        }
    }

    private void StartClassicRoulette()
    {
        bool exclude = ChkExcludePicked.IsChecked == true;
        _classicFinalPicked = _studentService.PickRandom(exclude);

        if (_classicFinalPicked == null)
        {
            MessageBox.Show("추첨할 학생이 없습니다.", "안내", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        BtnLaunch.IsEnabled = false;
        _classicShuffleCount = 0;

        if (_classicShuffleTimer == null)
        {
            _classicShuffleTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(50) };
            _classicShuffleTimer.Tick += ClassicShuffleTimer_Tick;
        }
        _classicShuffleTimer.Start();
    }

    private void ClassicShuffleTimer_Tick(object? sender, EventArgs e)
    {
        _classicShuffleCount++;
        if (_studentService.Students.Count > 0)
        {
            int rndIndex = Random.Shared.Next(_studentService.Students.Count);
            var temp = _studentService.Students[rndIndex];
            TxtClassicWinnerNumber.Text = $"{temp.Number}번";
            TxtClassicWinnerName.Text = $"{temp.Name} ({temp.AvatarName})";
        }

        if (_classicShuffleCount > 18)
        {
            _classicShuffleTimer?.Stop();
            BtnLaunch.IsEnabled = true;

            if (_classicFinalPicked != null)
            {
                TxtClassicWinnerNumber.Text = $"🎉 {_classicFinalPicked.Number}번 🎉";
                TxtClassicWinnerName.Text = $"{_classicFinalPicked.Name} ({_classicFinalPicked.AvatarName})";
            }

            if (_soundEnabled) _soundService.PlayChime();
            UpdateStatus();
        }
    }

    #endregion

    #region Toolbar Actions

    private void BtnManageRoster_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new StudentRosterManageDialog(_studentService)
        {
            Owner = this
        };
        if (dlg.ShowDialog() == true)
        {
            UpdateStatus();
        }
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        _studentService.ResetPicked();
        UpdateStatus();
        MessageBox.Show("제외 목록이 초기화되었습니다. 모든 학생이 다시 추첨에 포함됩니다.", "초기화 완료", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void BtnSoundToggle_Click(object sender, RoutedEventArgs e)
    {
        _soundEnabled = !_soundEnabled;
        BtnSoundToggle.Content = _soundEnabled ? "배경음 / 효과음 ON" : "효과음 OFF";
        BtnSoundToggle.Foreground = _soundEnabled ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8")) : Brushes.Gray;
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        _gameTimer?.Stop();
        _classicShuffleTimer?.Stop();
        e.Cancel = true;
        Hide();
    }

    #endregion
}

#region Helper Physics Classes (PinballBall, PinballPeg, PinballBumper, ConfettiParticle)

public class PinballBall
{
    public StudentItem Student { get; }
    public double X { get; set; }
    public double Y { get; set; }
    public double Vx { get; set; }
    public double Vy { get; set; }
    public double Radius { get; }
    public bool IsSettled { get; set; } = false;

    public Grid Visual { get; }
    private readonly Ellipse _leaderRing;

    public PinballBall(StudentItem student, double x, double y, double radius)
    {
        Student = student;
        X = x;
        Y = y;
        Radius = radius;

        Visual = new Grid
        {
            Width = radius * 2,
            Height = radius * 2
        };

        // Circular Avatar Ellipse with neon border
        var ellipse = new Ellipse
        {
            Width = radius * 2,
            Height = radius * 2,
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F0C95A")),
            StrokeThickness = 2.5
        };

        try
        {
            ellipse.Fill = new ImageBrush(new BitmapImage(new Uri(student.AvatarUri, UriKind.RelativeOrAbsolute)))
            {
                Stretch = Stretch.UniformToFill
            };
        }
        catch
        {
            ellipse.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B"));
        }
        Visual.Children.Add(ellipse);

        _leaderRing = new Ellipse
        {
            Width = radius * 2,
            Height = radius * 2,
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFF2A8")),
            StrokeThickness = 4,
            Visibility = Visibility.Collapsed,
            IsHitTestVisible = false
        };
        Visual.Children.Add(_leaderRing);

        // Number Badge
        var badge = new Border
        {
            Background = new SolidColorBrush(Color.FromArgb(220, 15, 23, 42)),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(4, 1, 4, 1),
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Bottom,
            Margin = new Thickness(0, 0, 0, 1)
        };
        badge.Child = new TextBlock
        {
            Text = $"{student.Number}",
            FontSize = 9,
            FontWeight = FontWeights.Bold,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")),
            HorizontalAlignment = HorizontalAlignment.Center
        };
        Visual.Children.Add(badge);

        UpdateVisual();
    }

    public void SetLeader(bool isLeader)
    {
        _leaderRing.Visibility = isLeader ? Visibility.Visible : Visibility.Collapsed;
        Panel.SetZIndex(Visual, isLeader ? 50 : 10);
    }

    public void UpdateVisual()
    {
        Canvas.SetLeft(Visual, X - Radius);
        Canvas.SetTop(Visual, Y - Radius);
    }
}

public class PinballPeg
{
    public double X { get; }
    public double Y { get; }
    public double Radius { get; }

    public Ellipse Visual { get; }
    public Ellipse GlowRing { get; }
    private double _flashTimer = 0;

    public PinballPeg(double x, double y, double radius)
    {
        X = x;
        Y = y;
        Radius = radius;

        Visual = new Ellipse
        {
            Width = radius * 2,
            Height = radius * 2,
            Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#C79445")),
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#684522")),
            StrokeThickness = 1.5
        };
        Canvas.SetLeft(Visual, x - radius);
        Canvas.SetTop(Visual, y - radius);

        GlowRing = new Ellipse
        {
            Width = radius * 4,
            Height = radius * 4,
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#8BCF8F")),
            StrokeThickness = 2,
            Opacity = 0
        };
        Canvas.SetLeft(GlowRing, x - radius * 2);
        Canvas.SetTop(GlowRing, y - radius * 2);
    }

    public void Flash()
    {
        _flashTimer = 0.25;
        GlowRing.Opacity = 0.9;
        Visual.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFFFFF"));
    }

    public void Update(double dt)
    {
        if (_flashTimer > 0)
        {
            _flashTimer -= dt;
            GlowRing.Opacity = Math.Max(0, _flashTimer / 0.25);
            if (_flashTimer <= 0)
            {
                Visual.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#C79445"));
            }
        }
    }
}

public class PinballBumper
{
    public double X { get; }
    public double Y { get; }
    public double Radius { get; }

    public Border Visual { get; }
    private double _flashTimer = 0;
    private readonly string _baseColor;

    public PinballBumper(double x, double y, double radius, string colorHex, string icon = "🍄")
    {
        X = x;
        Y = y;
        Radius = radius;
        _baseColor = colorHex;

        Visual = new Border
        {
            Width = radius * 2,
            Height = radius * 2,
            CornerRadius = new CornerRadius(radius),
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colorHex)),
            BorderBrush = Brushes.White,
            BorderThickness = new Thickness(3)
        };
        Visual.Child = new TextBlock
        {
            Text = icon,
            FontSize = radius >= 30 ? 22 : 17,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            Foreground = Brushes.White
        };

        Canvas.SetLeft(Visual, x - radius);
        Canvas.SetTop(Visual, y - radius);
    }

    public void Flash()
    {
        _flashTimer = 0.3;
        Visual.Background = Brushes.White;
    }

    public void Update(double dt)
    {
        if (_flashTimer > 0)
        {
            _flashTimer -= dt;
            if (_flashTimer <= 0)
            {
                Visual.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(_baseColor));
            }
        }
    }
}

public class PinballRail
{
    public double X1 { get; }
    public double Y1 { get; }
    public double X2 { get; }
    public double Y2 { get; }
    public double HalfThickness { get; }
    public double Restitution { get; } = 0.62;

    public Grid Visual { get; }
    private readonly Border _wood;
    private double _flashTimer;

    public PinballRail(double x1, double y1, double x2, double y2, double halfThickness, string colorHex, string label)
    {
        X1 = x1;
        Y1 = y1;
        X2 = x2;
        Y2 = y2;
        HalfThickness = halfThickness;

        double dx = x2 - x1;
        double dy = y2 - y1;
        double length = Math.Sqrt(dx * dx + dy * dy);
        double angle = Math.Atan2(dy, dx) * 180.0 / Math.PI;

        Visual = new Grid
        {
            Width = length,
            Height = halfThickness * 2 + 8,
            RenderTransformOrigin = new Point(0.5, 0.5),
            RenderTransform = new RotateTransform(angle),
            IsHitTestVisible = false
        };

        _wood = new Border
        {
            Height = halfThickness * 2,
            CornerRadius = new CornerRadius(halfThickness),
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colorHex)),
            BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#C99759")),
            BorderThickness = new Thickness(2),
            VerticalAlignment = VerticalAlignment.Center
        };

        var grain = new Border
        {
            Height = 3,
            Margin = new Thickness(15, 0, 15, 0),
            CornerRadius = new CornerRadius(2),
            Background = new SolidColorBrush(Color.FromArgb(85, 255, 226, 168)),
            VerticalAlignment = VerticalAlignment.Center
        };

        var tag = new TextBlock
        {
            Text = label == "통나무" ? "🍃" : label == "뿌리" ? "🌱" : "🍂",
            FontSize = 15,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            Opacity = 0.86
        };

        Visual.Children.Add(_wood);
        Visual.Children.Add(grain);
        Visual.Children.Add(tag);

        Canvas.SetLeft(Visual, (x1 + x2) / 2 - length / 2);
        Canvas.SetTop(Visual, (y1 + y2) / 2 - Visual.Height / 2);
    }

    public void Flash()
    {
        _flashTimer = 0.18;
        _wood.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F6D365"));
        _wood.BorderThickness = new Thickness(3);
    }

    public void Update(double dt)
    {
        if (_flashTimer <= 0) return;
        _flashTimer -= dt;
        if (_flashTimer <= 0)
        {
            _wood.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#C99759"));
            _wood.BorderThickness = new Thickness(2);
        }
    }
}

public class ConfettiParticle
{
    public double X { get; set; }
    public double Y { get; set; }
    public double Vx { get; set; }
    public double Vy { get; set; }
    public double Life { get; set; } = 1.8;
    public bool IsDead => Life <= 0;

    public Rectangle Visual { get; }

    public ConfettiParticle(double x, double y, double vx, double vy, string colorHex)
    {
        X = x;
        Y = y;
        Vx = vx;
        Vy = vy;

        Visual = new Rectangle
        {
            Width = 10,
            Height = 10,
            Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colorHex)),
            RenderTransform = new RotateTransform(0)
        };
        UpdateVisual();
    }

    public void Update(double dt)
    {
        Life -= dt;
        Vy += 450 * dt; // gravity
        X += Vx * dt;
        Y += Vy * dt;

        Visual.Opacity = Math.Clamp(Life / 1.5, 0, 1);
        UpdateVisual();
    }

    private void UpdateVisual()
    {
        Canvas.SetLeft(Visual, X);
        Canvas.SetTop(Visual, Y);
    }
}

#endregion
