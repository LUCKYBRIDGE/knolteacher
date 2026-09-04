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
    private readonly List<ConfettiParticle> _confetti = new();

    private DispatcherTimer? _gameTimer;
    private DispatcherTimer? _classicShuffleTimer;
    private int _classicShuffleCount = 0;
    private StudentItem? _classicFinalPicked;

    private bool _isPlaying = false;
    private bool _soundEnabled = true;
    private StudentItem? _lastWinner = null;
    private DateTime _lastFrameTime = DateTime.UtcNow;

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

    #region Physics Field Setup

    private void SetupPegsAndBumpers()
    {
        _pegs.Clear();
        _bumpers.Clear();

        // Staggered Triangular Pachinko Peg Grid
        int rows = 7;
        double startY = 220;
        double rowSpacing = 65;

        for (int r = 0; r < rows; r++)
        {
            int cols = 6 + (r % 2);
            double colSpacing = 68;
            double startX = 400 - ((cols - 1) * colSpacing) / 2.0;
            double y = startY + r * rowSpacing;

            for (int c = 0; c < cols; c++)
            {
                double x = startX + c * colSpacing;
                // Leave center hole open in rows 2 & 4 for Bumpers
                if (r == 2 && (c == 2 || c == 3)) continue;
                if (r == 4 && (c == 2 || c == 3 || c == 4)) continue;

                var peg = new PinballPeg(x, y, 7);
                _pegs.Add(peg);

                // Add visual element to canvas
                PinballCanvas.Children.Add(peg.GlowRing);
                PinballCanvas.Children.Add(peg.Visual);
            }
        }

        // Bouncy Neon Bumpers in the middle
        var b1 = new PinballBumper(330, 350, 30, "#38BDF8");
        var b2 = new PinballBumper(470, 350, 30, "#38BDF8");
        var b3 = new PinballBumper(400, 480, 34, "#EC4899");

        _bumpers.Add(b1);
        _bumpers.Add(b2);
        _bumpers.Add(b3);

        foreach (var b in _bumpers)
        {
            PinballCanvas.Children.Add(b.Visual);
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
        double spawnWidth = 340;
        double startX = 230;

        for (int i = 0; i < count; i++)
        {
            var student = toDrop[i];
            double x = startX + (i % 8) * (spawnWidth / 8.0) + (rand.NextDouble() * 10 - 5);
            double y = 18 - (i / 8) * 55; // staggered stacked above top funnel
            double vx = (rand.NextDouble() - 0.5) * 60;
            double vy = 40 + rand.NextDouble() * 80;

            var ball = new PinballBall(student, x, y, 22)
            {
                Vx = vx,
                Vy = vy
            };

            _balls.Add(ball);
            PinballCanvas.Children.Add(ball.Visual);
        }

        _isPlaying = true;
        BtnLaunch.IsEnabled = false;
        TxtBtnLaunchLabel.Text = "핀볼 질주 중...";
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

        double gravity = 760; // px/s^2
        double damp = 0.992;
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
            double leftWall = 30;
            double rightWall = 770;
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

            // Funnel walls (slanted deflectors at upper sides)
            if (b.Y < 380)
            {
                // Left triangle
                double leftSlopeX = (380 - b.Y) * (70.0 / 380.0);
                if (b.X - b.Radius < leftSlopeX)
                {
                    b.X = leftSlopeX + b.Radius;
                    b.Vx = Math.Abs(b.Vx) * 0.8 + 30;
                }
                // Right triangle
                double rightSlopeX = 800 - (380 - b.Y) * (70.0 / 380.0);
                if (b.X + b.Radius > rightSlopeX)
                {
                    b.X = rightSlopeX - b.Radius;
                    b.Vx = -Math.Abs(b.Vx) * 0.8 - 30;
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

            // 4.5 Bottom Inward Funnel Guides (channeling towards Champion Cup between Y=560 and Y=730)
            if (b.Y >= 560 && b.Y < 730)
            {
                double leftSlope = (b.Y - 560) * (300.0 / 170.0);
                if (b.X - b.Radius < leftSlope)
                {
                    b.X = leftSlope + b.Radius;
                    b.Vx = Math.Abs(b.Vx) * 0.7 + 35;
                }
                double rightSlope = 800 - (b.Y - 560) * (300.0 / 170.0);
                if (b.X + b.Radius > rightSlope)
                {
                    b.X = rightSlope - b.Radius;
                    b.Vx = -Math.Abs(b.Vx) * 0.7 - 35;
                }
            }

            // 5. Bottom Winning Cup Detection
            // Champion cup is at Left: 300, Top: 730, Width: 200, Height: 110
            if (b.Y + b.Radius >= 740 && b.X >= 310 && b.X <= 490)
            {
                // Winner!
                b.IsSettled = true;
                b.Vx = 0;
                b.Vy = 0;
                b.Y = 760;

                if (_lastWinner == null)
                {
                    _lastWinner = b.Student;
                    TriggerWinnerCelebration(b.Student);
                }
            }
            else if (b.Y > 770)
            {
                // Dropped into side tray
                b.IsSettled = true;
                b.Vx = 0;
                b.Vy = 0;
                b.Y = 780;
            }

            b.UpdateVisual();
        }

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
                var fallbackWinner = _balls.OrderBy(b => Math.Abs(b.X - 400)).First().Student;
                TriggerWinnerCelebration(fallbackWinner);
            }
            _gameTimer?.Stop();
            _isPlaying = false;
            BtnLaunch.IsEnabled = true;
            TxtBtnLaunchLabel.Text = "핀볼 일제 발사! (추첨)";
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
        SpawnConfetti(400, 420, 75);

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
        TxtBtnLaunchLabel.Text = "핀볼 일제 발사! (추첨)";
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
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8")),
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
            Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")),
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CA8A04")),
            StrokeThickness = 1.5
        };
        Canvas.SetLeft(Visual, x - radius);
        Canvas.SetTop(Visual, y - radius);

        GlowRing = new Ellipse
        {
            Width = radius * 4,
            Height = radius * 4,
            Stroke = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8")),
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
                Visual.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047"));
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

    public PinballBumper(double x, double y, double radius, string colorHex)
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
            Text = "⚡",
            FontSize = 16,
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
