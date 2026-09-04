using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public class ScoreDataModel
{
    public string[] Names { get; set; } = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠" };
    public int[] Scores { get; set; } = new int[6];
}

public partial class ScoreWidgetView : UserControl
{
    private readonly int[] _scores = new int[6];
    private readonly string[] _names = new[] { "1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠" };
    private readonly string _stateFile;
    private bool _isLoaded = false;

    public ScoreWidgetView()
    {
        InitializeComponent();

        string dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _stateFile = Path.Combine(dir, "board_scores.json");

        Loaded += (s, e) =>
        {
            LoadState();
            _isLoaded = true;
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
                    if (data.Scores != null && data.Scores.Length == 6)
                    {
                        Array.Copy(data.Scores, _scores, 6);
                    }
                    if (data.Names != null && data.Names.Length == 6)
                    {
                        Array.Copy(data.Names, _names, 6);
                    }
                }
            }
            catch { }
        }

        UpdateUi();
    }

    private void SaveState()
    {
        try
        {
            var data = new ScoreDataModel
            {
                Names = _names,
                Scores = _scores
            };
            string json = JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(_stateFile, json);
        }
        catch { }
    }

    private void UpdateUi()
    {
        TbName1.Text = _names[0];
        TbName2.Text = _names[1];
        TbName3.Text = _names[2];
        TbName4.Text = _names[3];
        TbName5.Text = _names[4];
        TbName6.Text = _names[5];

        TbScore1.Text = _scores[0].ToString();
        TbScore2.Text = _scores[1].ToString();
        TbScore3.Text = _scores[2].ToString();
        TbScore4.Text = _scores[3].ToString();
        TbScore5.Text = _scores[4].ToString();
        TbScore6.Text = _scores[5].ToString();
    }

    private void BtnScore_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            var parts = tag.Split(',');
            if (parts.Length == 2 && int.TryParse(parts[0], out int grp) && int.TryParse(parts[1], out int delta))
            {
                int idx = grp - 1;
                if (idx >= 0 && idx < 6)
                {
                    _scores[idx] = Math.Max(0, _scores[idx] + delta);
                    UpdateScoreDisplay(idx);
                    SaveState();
                }
            }
        }
    }

    private void UpdateScoreDisplay(int idx)
    {
        TextBox? tb = idx switch
        {
            0 => TbScore1,
            1 => TbScore2,
            2 => TbScore3,
            3 => TbScore4,
            4 => TbScore5,
            5 => TbScore6,
            _ => null
        };

        if (tb != null)
        {
            tb.Text = _scores[idx].ToString();
        }
    }

    private void Score_LostFocus(object sender, RoutedEventArgs e)
    {
        if (!_isLoaded) return;
        if (sender is TextBox tb && tb.Tag is string tagStr && int.TryParse(tagStr, out int grp))
        {
            int idx = grp - 1;
            if (idx >= 0 && idx < 6)
            {
                if (int.TryParse(tb.Text.Trim(), out int val))
                {
                    _scores[idx] = Math.Max(0, val);
                }
                tb.Text = _scores[idx].ToString();
                SaveState();
            }
        }
    }

    private void Score_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            Score_LostFocus(sender, e);
            Keyboard.ClearFocus();
        }
    }

    private void Name_LostFocus(object sender, RoutedEventArgs e)
    {
        if (!_isLoaded) return;
        _names[0] = string.IsNullOrWhiteSpace(TbName1.Text) ? "1모둠" : TbName1.Text.Trim();
        _names[1] = string.IsNullOrWhiteSpace(TbName2.Text) ? "2모둠" : TbName2.Text.Trim();
        _names[2] = string.IsNullOrWhiteSpace(TbName3.Text) ? "3모둠" : TbName3.Text.Trim();
        _names[3] = string.IsNullOrWhiteSpace(TbName4.Text) ? "4모둠" : TbName4.Text.Trim();
        _names[4] = string.IsNullOrWhiteSpace(TbName5.Text) ? "5모둠" : TbName5.Text.Trim();
        _names[5] = string.IsNullOrWhiteSpace(TbName6.Text) ? "6모둠" : TbName6.Text.Trim();
        SaveState();
    }

    private void BtnAddAll_Click(object sender, RoutedEventArgs e)
    {
        for (int i = 0; i < 6; i++)
        {
            _scores[i] = _scores[i] + 1;
        }
        UpdateUi();
        SaveState();
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("모든 모둠의 점수를 0점으로 초기화하시겠습니까?", "점수 초기화", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            Array.Clear(_scores, 0, _scores.Length);
            UpdateUi();
            SaveState();
        }
    }
}
