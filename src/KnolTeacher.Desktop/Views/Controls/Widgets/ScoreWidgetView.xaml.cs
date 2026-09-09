using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public class ScoreDataModel
{
    public int GroupCount { get; set; } = 6;
    public string[] Names { get; set; } = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠", "7모둠", "8모둠" };
    public int[] Scores { get; set; } = new int[8];
}

public partial class ScoreWidgetView : UserControl
{
    private int _groupCount = 6;
    private readonly int[] _scores = new int[8];
    private readonly string[] _names = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠", "7모둠", "8모둠" };
    private readonly string _stateFile;
    private bool _isLoaded = false;

    public ScoreWidgetView()
    {
        InitializeComponent();

        string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _stateFile = Path.Combine(dir, "board_scores.json");

        Loaded += (s, e) =>
        {
            if (!_isLoaded)
            {
                LoadState();
                _isLoaded = true;
                BuildUi();
            }
        };
    }

    private void LoadState()
    {
        if (File.Exists(_stateFile))
        {
            try
            {
                string json = File.ReadAllText(_stateFile);
                var data = JsonSerializer.Deserialize<ScoreDataModel>(json);
                if (data != null)
                {
                    if (data.GroupCount >= 2 && data.GroupCount <= 8)
                    {
                        _groupCount = data.GroupCount;
                    }
                    if (data.Scores != null)
                    {
                        int len = Math.Min(data.Scores.Length, _scores.Length);
                        Array.Copy(data.Scores, _scores, len);
                    }
                    if (data.Names != null)
                    {
                        int len = Math.Min(data.Names.Length, _names.Length);
                        Array.Copy(data.Names, _names, len);
                    }
                }
            }
            catch { }
        }

        // Set combo box
        for (int i = 0; i < CbGroupCount.Items.Count; i++)
        {
            if (CbGroupCount.Items[i] is ComboBoxItem item &&
                int.TryParse(item.Tag?.ToString(), out int cnt) &&
                cnt == _groupCount)
            {
                CbGroupCount.SelectedIndex = i;
                break;
            }
        }
    }

    private void SaveState()
    {
        try
        {
            var data = new ScoreDataModel
            {
                GroupCount = _groupCount,
                Names = _names,
                Scores = _scores
            };
            string json = JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(_stateFile, json);
        }
        catch { }
    }

    private void BuildUi()
    {
        GridGroups.Children.Clear();

        // Determine Columns & Rows for optimal appearance
        if (_groupCount == 2) { GridGroups.Columns = 2; GridGroups.Rows = 1; }
        else if (_groupCount == 3) { GridGroups.Columns = 3; GridGroups.Rows = 1; }
        else if (_groupCount == 4) { GridGroups.Columns = 2; GridGroups.Rows = 2; }
        else if (_groupCount <= 6) { GridGroups.Columns = 3; GridGroups.Rows = 2; }
        else { GridGroups.Columns = 4; GridGroups.Rows = 2; }

        for (int i = 0; i < _groupCount; i++)
        {
            int idx = i;
            var border = new Border
            {
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0F172A")),
                CornerRadius = new CornerRadius(8),
                BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")),
                BorderThickness = new Thickness(1),
                Margin = new Thickness(2),
                Padding = new Thickness(4)
            };

            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Name TextBox
            var tbName = new TextBox
            {
                Text = _names[idx],
                FontSize = 11,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8")),
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")),
                BorderThickness = new Thickness(1),
                TextAlignment = TextAlignment.Center,
                Padding = new Thickness(2, 1, 2, 1),
                Margin = new Thickness(2, 0, 2, 2)
            };
            tbName.LostFocus += (s, e) =>
            {
                _names[idx] = string.IsNullOrWhiteSpace(tbName.Text) ? $"{idx + 1}모둠" : tbName.Text.Trim();
                SaveState();
            };
            Grid.SetRow(tbName, 0);
            grid.Children.Add(tbName);

            // Score Viewbox & TextBox
            var viewbox = new Viewbox { Stretch = Stretch.Uniform, Margin = new Thickness(0, 1, 0, 1) };
            var tbScore = new TextBox
            {
                Text = _scores[idx].ToString(),
                MinWidth = 40,
                FontSize = 32,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8")),
                Background = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                TextAlignment = TextAlignment.Center
            };
            tbScore.LostFocus += (s, e) =>
            {
                if (int.TryParse(tbScore.Text.Trim(), out int val))
                {
                    _scores[idx] = Math.Max(0, val);
                }
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };
            tbScore.KeyDown += (s, e) =>
            {
                if (e.Key == Key.Enter)
                {
                    Keyboard.ClearFocus();
                }
            };
            viewbox.Child = tbScore;
            Grid.SetRow(viewbox, 1);
            grid.Children.Add(viewbox);

            // Buttons: -1, +1, +5
            var spButtons = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0, 2, 0, 0)
            };

            var btnMinus = new Button
            {
                Content = "-1",
                Width = 22,
                Height = 20,
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155")),
                Foreground = Brushes.White,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 2, 0),
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand
            };
            btnMinus.Click += (s, e) =>
            {
                _scores[idx] = Math.Max(0, _scores[idx] - 1);
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            var btnPlus1 = new Button
            {
                Content = "+1",
                Width = 24,
                Height = 20,
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7")),
                Foreground = Brushes.White,
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 2, 0),
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand
            };
            btnPlus1.Click += (s, e) =>
            {
                _scores[idx] += 1;
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            var btnPlus5 = new Button
            {
                Content = "+5",
                Width = 24,
                Height = 20,
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0369A1")),
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FDE047")),
                FontSize = 10,
                FontWeight = FontWeights.Bold,
                BorderThickness = new Thickness(0),
                Cursor = Cursors.Hand
            };
            btnPlus5.Click += (s, e) =>
            {
                _scores[idx] += 5;
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            spButtons.Children.Add(btnMinus);
            spButtons.Children.Add(btnPlus1);
            spButtons.Children.Add(btnPlus5);

            Grid.SetRow(spButtons, 2);
            grid.Children.Add(spButtons);

            border.Child = grid;
            GridGroups.Children.Add(border);
        }
    }

    private void CbGroupCount_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;

        if (CbGroupCount.SelectedItem is ComboBoxItem item &&
            int.TryParse(item.Tag?.ToString(), out int cnt) &&
            cnt >= 2 && cnt <= 8)
        {
            _groupCount = cnt;
            BuildUi();
            SaveState();
        }
    }

    private void BtnAddAll_Click(object sender, RoutedEventArgs e)
    {
        for (int i = 0; i < _groupCount; i++)
        {
            _scores[i]++;
        }
        BuildUi();
        SaveState();
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("모든 모둠의 점수를 0점으로 초기화하시겠습니까?", "점수 초기화", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            Array.Clear(_scores, 0, _scores.Length);
            BuildUi();
            SaveState();
        }
    }
}
