using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public class ScoreDataModel
{
    public int GroupCount { get; set; } = 6;
    public string[] Names { get; set; } = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠", "7모둠", "8모둠" };
    public int[] Scores { get; set; } = new int[8];
}

public partial class ScoreWidgetView : UserControl
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private int _groupCount = 6;
    private readonly int[] _scores = new int[8];
    private readonly string[] _names = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠", "7모둠", "8모둠" };
    private readonly string _stateFile;
    private bool _isLoaded;

    public ScoreWidgetView(IConfigService? configService = null)
    {
        InitializeComponent();

        configService ??= (Application.Current as App)?.Services?.GetService(typeof(IConfigService)) as IConfigService;
        string dir = configService?.ConfigDir
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _stateFile = Path.Combine(dir, "board_scores.json");

        Loaded += (_, _) =>
        {
            if (_isLoaded) return;
            LoadState();
            _isLoaded = true;
            BuildUi();
        };
    }

    private void LoadState()
    {
        if (SafeLocalJsonStore.TryLoad<ScoreDataModel>(_stateFile, JsonOptions, out var data) && data != null)
        {
            if (data.GroupCount is >= 2 and <= 8)
            {
                _groupCount = data.GroupCount;
            }

            if (data.Scores != null)
            {
                Array.Copy(data.Scores, _scores, Math.Min(data.Scores.Length, _scores.Length));
            }

            if (data.Names != null)
            {
                Array.Copy(data.Names, _names, Math.Min(data.Names.Length, _names.Length));
            }
        }

        for (int i = 0; i < CbGroupCount.Items.Count; i++)
        {
            if (CbGroupCount.Items[i] is ComboBoxItem item &&
                int.TryParse(item.Tag?.ToString(), out int count) &&
                count == _groupCount)
            {
                CbGroupCount.SelectedIndex = i;
                break;
            }
        }
    }

    private void SaveState()
    {
        var data = new ScoreDataModel
        {
            GroupCount = _groupCount,
            Names = (string[])_names.Clone(),
            Scores = (int[])_scores.Clone()
        };

        if (!SafeLocalJsonStore.TrySave(_stateFile, data, JsonOptions))
        {
            System.Diagnostics.Debug.WriteLine("[Nolboard.Score] Local score state save failed.");
        }
    }

    private void BuildUi()
    {
        GridGroups.Children.Clear();

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
                Background = BrushFrom("#0F172A"),
                CornerRadius = new CornerRadius(8),
                BorderBrush = BrushFrom("#334155"),
                BorderThickness = new Thickness(1),
                Margin = new Thickness(2),
                Padding = new Thickness(4)
            };

            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            var tbName = new TextBox
            {
                Text = _names[idx],
                FontSize = 11,
                Foreground = BrushFrom("#94A3B8"),
                Background = BrushFrom("#1E293B"),
                BorderBrush = BrushFrom("#334155"),
                BorderThickness = new Thickness(1),
                TextAlignment = TextAlignment.Center,
                Padding = new Thickness(2, 1, 2, 1),
                Margin = new Thickness(2, 0, 2, 2)
            };
            tbName.LostFocus += (_, _) =>
            {
                _names[idx] = string.IsNullOrWhiteSpace(tbName.Text) ? $"{idx + 1}모둠" : tbName.Text.Trim();
                SaveState();
            };
            Grid.SetRow(tbName, 0);
            grid.Children.Add(tbName);

            var viewbox = new Viewbox { Stretch = Stretch.Uniform, Margin = new Thickness(0, 1, 0, 1) };
            var tbScore = new TextBox
            {
                Text = _scores[idx].ToString(),
                MinWidth = 40,
                FontSize = 32,
                FontWeight = FontWeights.Bold,
                Foreground = BrushFrom("#38BDF8"),
                Background = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                TextAlignment = TextAlignment.Center
            };
            tbScore.LostFocus += (_, _) =>
            {
                if (int.TryParse(tbScore.Text.Trim(), out int value))
                {
                    _scores[idx] = Math.Max(0, value);
                }
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };
            tbScore.KeyDown += (_, e) =>
            {
                if (e.Key == Key.Enter)
                {
                    Keyboard.ClearFocus();
                    e.Handled = true;
                }
            };
            viewbox.Child = tbScore;
            Grid.SetRow(viewbox, 1);
            grid.Children.Add(viewbox);

            var buttons = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0, 2, 0, 0)
            };

            Button minus = MakeScoreButton("-1", 22, "#334155", "#FFFFFF");
            minus.Margin = new Thickness(0, 0, 2, 0);
            minus.Click += (_, _) =>
            {
                _scores[idx] = Math.Max(0, _scores[idx] - 1);
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            Button plus1 = MakeScoreButton("+1", 24, "#0284C7", "#FFFFFF");
            plus1.Margin = new Thickness(0, 0, 2, 0);
            plus1.Click += (_, _) =>
            {
                _scores[idx]++;
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            Button plus5 = MakeScoreButton("+5", 24, "#0369A1", "#FDE047");
            plus5.Click += (_, _) =>
            {
                _scores[idx] += 5;
                tbScore.Text = _scores[idx].ToString();
                SaveState();
            };

            buttons.Children.Add(minus);
            buttons.Children.Add(plus1);
            buttons.Children.Add(plus5);
            Grid.SetRow(buttons, 2);
            grid.Children.Add(buttons);

            border.Child = grid;
            GridGroups.Children.Add(border);
        }
    }

    private void CbGroupCount_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_isLoaded) return;

        if (CbGroupCount.SelectedItem is ComboBoxItem item &&
            int.TryParse(item.Tag?.ToString(), out int count) &&
            count is >= 2 and <= 8)
        {
            _groupCount = count;
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
        if (MessageBox.Show("모든 모둠의 점수를 0점으로 초기화하시겠습니까?", "점수 초기화", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes)
        {
            return;
        }

        Array.Clear(_scores, 0, _scores.Length);
        BuildUi();
        SaveState();
    }

    private static Button MakeScoreButton(string content, double width, string background, string foreground)
        => new()
        {
            Content = content,
            Width = width,
            Height = 20,
            Background = BrushFrom(background),
            Foreground = BrushFrom(foreground),
            FontSize = 10,
            FontWeight = FontWeights.Bold,
            BorderThickness = new Thickness(0),
            Cursor = Cursors.Hand
        };

    private static SolidColorBrush BrushFrom(string hex)
        => new((Color)ColorConverter.ConvertFromString(hex));
}
