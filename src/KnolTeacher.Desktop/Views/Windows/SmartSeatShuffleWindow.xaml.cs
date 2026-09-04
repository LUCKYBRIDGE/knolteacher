using System;
using System.Collections.Generic;
using System.Linq;
using System.Media;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class SmartSeatShuffleWindow : Window
{
    private readonly IStudentManagerService _studentManager;
    private readonly IDisplayManager _displayManager;
    private readonly ISoundService _soundService;

    private int _rows = 4;
    private int _cols = 6;
    private bool _isTeacherPerspective = false;
    private bool _isFullscreen = false;
    private WindowState _prevWindowState;
    private WindowStyle _prevWindowStyle;

    private List<StudentItem?> _assignedSeats = new();
    private DispatcherTimer? _rollingTimer;
    private int _rollingTick = 0;
    private readonly Random _rand = new();

    public SmartSeatShuffleWindow(
        IStudentManagerService studentManager,
        IDisplayManager displayManager,
        ISoundService soundService)
    {
        InitializeComponent();
        _studentManager = studentManager;
        _displayManager = displayManager;
        _soundService = soundService;

        Closing += (s, e) =>
        {
            e.Cancel = true;
            _rollingTimer?.Stop();
            Hide();
        };

        Loaded += SmartSeatShuffleWindow_Loaded;
    }

    private void SmartSeatShuffleWindow_Loaded(object sender, RoutedEventArgs e)
    {
        // Populate combo options
        ComboRows.Items.Clear();
        ComboCols.Items.Clear();
        for (int r = 1; r <= 8; r++) ComboRows.Items.Add(r);
        for (int c = 1; c <= 8; c++) ComboCols.Items.Add(c);

        ComboRows.SelectedItem = _rows;
        ComboCols.SelectedItem = _cols;

        UpdateClassSize();
        InitializeDesks();
    }

    private void UpdateClassSize()
    {
        var students = _studentManager.Students;
        TxtClassSizeInfo.Text = $"학생 재적: {students.Count}명 (총 책상: {_rows * _cols}석)";
    }

    private void Dimensions_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ComboRows.SelectedItem is int r && ComboCols.SelectedItem is int c)
        {
            _rows = r;
            _cols = c;
            GridDesks.Rows = _rows;
            GridDesks.Columns = _cols;
            UpdateClassSize();
            InitializeDesks();
        }
    }

    private void BtnPresetPairs_Click(object sender, RoutedEventArgs e)
    {
        _rows = 4;
        _cols = 6;
        ComboRows.SelectedItem = _rows;
        ComboCols.SelectedItem = _cols;
    }

    private void BtnPresetGroups_Click(object sender, RoutedEventArgs e)
    {
        _rows = 4;
        _cols = 6;
        ComboRows.SelectedItem = _rows;
        ComboCols.SelectedItem = _cols;
    }

    private void BtnPresetExams_Click(object sender, RoutedEventArgs e)
    {
        _rows = 5;
        _cols = 5;
        ComboRows.SelectedItem = _rows;
        ComboCols.SelectedItem = _cols;
    }

    private void InitializeDesks()
    {
        int totalDesks = _rows * _cols;
        var students = _studentManager.Students.ToList();

        _assignedSeats.Clear();
        for (int i = 0; i < totalDesks; i++)
        {
            _assignedSeats.Add(i < students.Count ? students[i] : null);
        }

        RenderDesks();
    }

    private void RenderDesks()
    {
        GridDesks.Children.Clear();
        GridDesks.Rows = _rows;
        GridDesks.Columns = _cols;

        int totalDesks = _rows * _cols;
        var displayOrder = new List<int>();

        if (!_isTeacherPerspective)
        {
            // Student perspective: Row 0 is near blackboard (top)
            for (int i = 0; i < totalDesks; i++) displayOrder.Add(i);
        }
        else
        {
            // Teacher perspective: Invert rows so teacher podium is at bottom
            for (int r = _rows - 1; r >= 0; r--)
            {
                for (int c = 0; c < _cols; c++)
                {
                    displayOrder.Add((r * _cols) + c);
                }
            }
        }

        foreach (int index in displayOrder)
        {
            var student = index < _assignedSeats.Count ? _assignedSeats[index] : null;
            var deskCard = CreateDeskCard(index + 1, student);
            GridDesks.Children.Add(deskCard);
        }
    }

    private UIElement CreateDeskCard(int deskNumber, StudentItem? student)
    {
        var border = new Border
        {
            Width = 110,
            Height = 100,
            Margin = new Thickness(5),
            Background = (Brush)FindResource("BeigeCardInner"),
            BorderBrush = (Brush)FindResource("BeigeCardBorder"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(10),
            Padding = new Thickness(6)
        };

        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        // Desk Number Pill
        var numPill = new Border
        {
            Background = (Brush)FindResource("BeigeAccentSoft"),
            CornerRadius = new CornerRadius(4),
            Padding = new Thickness(4, 1, 4, 1),
            HorizontalAlignment = HorizontalAlignment.Left
        };
        numPill.Child = new TextBlock
        {
            Text = $"{deskNumber}",
            FontSize = 10,
            FontWeight = FontWeights.Bold,
            Foreground = (Brush)FindResource("BeigeAccent")
        };
        Grid.SetRow(numPill, 0);
        grid.Children.Add(numPill);

        if (student != null)
        {
            // Animal Avatar
            var imgBorder = new Border
            {
                Width = 44,
                Height = 44,
                CornerRadius = new CornerRadius(8),
                Background = (Brush)FindResource("BeigeCardBg"),
                BorderBrush = (Brush)FindResource("BeigeCardBorder"),
                BorderThickness = new Thickness(1),
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(0, 2, 0, 2)
            };

            var img = new Image
            {
                Width = 38,
                Height = 38,
                Stretch = Stretch.Uniform
            };

            try
            {
                string avatarPath = student.AvatarUri;
                img.Source = new BitmapImage(new Uri($"pack://application:,,,{avatarPath}", UriKind.Absolute));
            }
            catch
            {
                // Fallback icon
            }

            imgBorder.Child = img;
            Grid.SetRow(imgBorder, 1);
            grid.Children.Add(imgBorder);

            // Student Name & Number
            var nameBlock = new TextBlock
            {
                Text = $"{student.Number}. {student.Name}",
                FontWeight = FontWeights.Bold,
                FontSize = 12,
                Foreground = (Brush)FindResource("BeigeTextMain"),
                HorizontalAlignment = HorizontalAlignment.Center,
                TextTrimming = TextTrimming.CharacterEllipsis
            };
            Grid.SetRow(nameBlock, 2);
            grid.Children.Add(nameBlock);
        }
        else
        {
            // Empty desk
            var emptyStack = new StackPanel
            {
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            emptyStack.Children.Add(new TextBlock
            {
                Text = "🪑",
                FontSize = 24,
                HorizontalAlignment = HorizontalAlignment.Center,
                Opacity = 0.3
            });
            emptyStack.Children.Add(new TextBlock
            {
                Text = "빈 자리",
                FontSize = 11,
                Foreground = (Brush)FindResource("BeigeTextMuted"),
                HorizontalAlignment = HorizontalAlignment.Center
            });
            Grid.SetRow(emptyStack, 1);
            grid.Children.Add(emptyStack);
        }

        border.Child = grid;
        return border;
    }

    private void BtnShuffle_Click(object sender, RoutedEventArgs e)
    {
        if (ChkRollingAnimation.IsChecked == true)
        {
            StartRollingShuffle();
        }
        else
        {
            PerformFinalShuffle();
        }
    }

    private void StartRollingShuffle()
    {
        BtnShuffle.IsEnabled = false;
        _rollingTick = 0;

        _rollingTimer?.Stop();
        _rollingTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(70)
        };

        var allStudents = _studentManager.Students;

        _rollingTimer.Tick += (s, e) =>
        {
            _rollingTick++;

            // Randomly flash desks
            var randomized = allStudents.OrderBy(_ => _rand.Next()).Cast<StudentItem?>().ToList();
            int totalDesks = _rows * _cols;
            while (randomized.Count < totalDesks) randomized.Add(null);
            _assignedSeats = randomized.Take(totalDesks).ToList();
            RenderDesks();

            if (_rollingTick >= 25)
            {
                _rollingTimer.Stop();
                PerformFinalShuffle();
                BtnShuffle.IsEnabled = true;

                try
                {
                    SystemSounds.Asterisk.Play();
                }
                catch { }
            }
        };

        _rollingTimer.Start();
    }

    private void PerformFinalShuffle()
    {
        var students = _studentManager.Students.OrderBy(_ => _rand.Next()).ToList();
        int totalDesks = _rows * _cols;

        var finalSeats = new List<StudentItem?>();

        if (ChkGenderPair.IsChecked == true)
        {
            // Pair boys and girls where possible
            var boys = students.Where(s => s.Gender == "남" || s.Gender == "M").ToList();
            var girls = students.Where(s => s.Gender == "여" || s.Gender == "F").ToList();
            var others = students.Where(s => !boys.Contains(s) && !girls.Contains(s)).ToList();

            var paired = new List<StudentItem>();
            int maxPairs = Math.Min(boys.Count, girls.Count);

            for (int i = 0; i < maxPairs; i++)
            {
                paired.Add(boys[i]);
                paired.Add(girls[i]);
            }
            paired.AddRange(boys.Skip(maxPairs));
            paired.AddRange(girls.Skip(maxPairs));
            paired.AddRange(others);

            for (int i = 0; i < totalDesks; i++)
            {
                finalSeats.Add(i < paired.Count ? paired[i] : null);
            }
        }
        else
        {
            for (int i = 0; i < totalDesks; i++)
            {
                finalSeats.Add(i < students.Count ? students[i] : null);
            }
        }

        _assignedSeats = finalSeats;
        RenderDesks();
    }

    private void BtnTogglePerspective_Click(object sender, RoutedEventArgs e)
    {
        _isTeacherPerspective = !_isTeacherPerspective;

        if (_isTeacherPerspective)
        {
            TxtBoardTitle.Text = "👨‍🏫  교  탁  (선생님 시선 - 앞쪽)  👨‍🏫";
            BannerBoard.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#92400E"));
            BannerBoard.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B45309"));
            TxtBoardTitle.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEF3C7"));
        }
        else
        {
            TxtBoardTitle.Text = "🟩  칠  판  (학생 시선 - 앞 쪽)  🟩";
            BannerBoard.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#14532D"));
            BannerBoard.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#166534"));
            TxtBoardTitle.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#BBF7D0"));
        }

        RenderDesks();
    }

    private void BtnCopySeating_Click(object sender, RoutedEventArgs e)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"[학급 자리 배치표 ({_rows}행 × {_cols}열)]");
        sb.AppendLine($"----------------------------------------");
        sb.AppendLine($"        [ 칠 판 / 교 탁 ]              ");
        sb.AppendLine($"----------------------------------------");

        for (int r = 0; r < _rows; r++)
        {
            var rowNames = new List<string>();
            for (int c = 0; c < _cols; c++)
            {
                int idx = (r * _cols) + c;
                var st = idx < _assignedSeats.Count ? _assignedSeats[idx] : null;
                string name = st != null ? $"{st.Number}.{st.Name}" : "(빈자리)";
                rowNames.Add(name.PadRight(10));
            }
            sb.AppendLine(string.Join("  |  ", rowNames));
        }

        try
        {
            Clipboard.SetText(sb.ToString());
            MessageBox.Show("자리 배치표가 클립보드에 복사되었습니다!\n한글(HWP)이나 메신저에 붙여넣기(Ctrl+V) 하실 수 있습니다.", "복사 완료", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"복사 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        _displayManager.MoveToStudentMonitor(this, maximize: false);
    }

    private void BtnFullscreen_Click(object sender, RoutedEventArgs e)
    {
        if (!_isFullscreen)
        {
            _prevWindowState = WindowState;
            _prevWindowStyle = WindowStyle;
            WindowStyle = WindowStyle.None;
            WindowState = WindowState.Maximized;
            _isFullscreen = true;
            BtnFullscreen.Content = "🗗 창모드";
        }
        else
        {
            WindowStyle = _prevWindowStyle;
            WindowState = _prevWindowState;
            _isFullscreen = false;
            BtnFullscreen.Content = "⛶ 전체화면";
        }
    }
}
