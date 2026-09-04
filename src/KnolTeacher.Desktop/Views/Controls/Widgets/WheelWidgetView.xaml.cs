using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class WheelWidgetView : UserControl
{
    private readonly ISoundService? _soundService;
    private List<string> _activeItems = new();
    private bool _isSpinning = false;
    private bool _isReady = false;

    public WheelWidgetView(ISoundService? soundService = null)
    {
        _soundService = soundService;
        InitializeComponent();
        _isReady = true;
        LoadPreset(0);
    }

    private void LoadPreset(int index)
    {
        string text = index switch
        {
            1 => string.Join(", ", Enumerable.Range(1, 25).Select(i => $"{i}번")),
            2 => "국어, 수학, 사회, 과학, 영어, 음악, 미술, 체육, 도덕, 실과",
            3 => "칠판지우개, 우유당번, 환기반장, 줄서기도우미, 정리정돈, 책장정리",
            4 => string.IsNullOrWhiteSpace(TbCustomItems.Text) ? "사과, 바나나, 포도, 딸기, 오렌지" : TbCustomItems.Text,
            _ => "1모둠, 2모둠, 3모둠, 4모둠, 5모둠, 6모둠"
        };

        TbCustomItems.Text = text;
        UpdateActiveItemsFromText();

        if (index == 4)
        {
            PanelCustomInput.Visibility = Visibility.Visible;
            BtnToggleEdit.Content = "▲ 접기";
        }
    }

    private void CbPresets_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_isReady) return;
        LoadPreset(CbPresets.SelectedIndex);
    }

    private void BtnToggleEdit_Click(object sender, RoutedEventArgs e)
    {
        if (PanelCustomInput.Visibility == Visibility.Visible)
        {
            PanelCustomInput.Visibility = Visibility.Collapsed;
            BtnToggleEdit.Content = "✏️ 항목 편집";
        }
        else
        {
            PanelCustomInput.Visibility = Visibility.Visible;
            BtnToggleEdit.Content = "▲ 접기";
        }
    }

    private void TbCustomItems_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (!_isReady) return;
        UpdateActiveItemsFromText();
    }

    private void UpdateActiveItemsFromText()
    {
        if (TbCustomItems == null) return;
        string raw = TbCustomItems.Text;
        var parts = raw.Split(new[] { ',', '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries)
                       .Select(s => s.Trim())
                       .Where(s => !string.IsNullOrEmpty(s))
                       .ToList();

        _activeItems = parts.Count > 0 ? parts : new List<string> { "항목 없음" };
        if (TxtItemCount != null)
        {
            TxtItemCount.Text = $"총 {_activeItems.Count}개 항목 등록됨";
        }
    }

    private async void BtnSpin_Click(object sender, RoutedEventArgs e)
    {
        if (_isSpinning || _activeItems.Count == 0) return;
        _isSpinning = true;
        BtnSpin.IsEnabled = false;

        var rng = new Random();
        for (int i = 0; i < 15; i++)
        {
            string temp = _activeItems[rng.Next(_activeItems.Count)];
            TxtResult.Text = $"▶ {temp}";
            TxtResult.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
            await Task.Delay(35 + i * 12);
        }

        string winner = _activeItems[rng.Next(_activeItems.Count)];
        TxtResult.Text = $"🎉 {winner}!";
        TxtResult.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));

        _soundService?.PlayChime();
        _isSpinning = false;
        BtnSpin.IsEnabled = true;
    }
}
