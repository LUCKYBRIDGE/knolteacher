using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public class DiceStatRow
{
    public int Face { get; set; }
    public int Count { get; set; }
    public string CountStr => $"{Count}회";
    public string RatioStr { get; set; } = "0.000";
    public string PercentStr { get; set; } = "0.0%";
}

public partial class DiceWidgetView : UserControl, IWidgetLifecycle
{
    private readonly ISoundService? _soundService;
    private static readonly Dictionary<int, string> DiceChars = new()
    {
        { 1, "⚀" }, { 2, "⚁" }, { 3, "⚂" }, { 4, "⚃" }, { 5, "⚄" }, { 6, "⚅" }
    };

    private int _diceCount = 1;
    private int _maxFace = 6;
    private readonly Dictionary<int, int> _faceCounts = new();
    private CancellationTokenSource? _rollCts;
    private int _totalThrows = 0;
    private bool _isRolling = false;
    private bool _isReady = false;
    private bool _isActive = false;
    private bool _disposed = false;

    public DiceWidgetView(ISoundService? soundService = null)
    {
        _soundService = soundService;
        InitializeComponent();
        _isReady = true;
        UpdateDisplay(6, null);
        UpdateStatsTable();
    }

    public void Activate()
    {
        if (_disposed) return;
        _isActive = true;
    }

    public void Deactivate()
    {
        if (_disposed || !_isActive) return;
        _isActive = false;
        CancelRoll();
    }

    public void Dispose()
    {
        if (_disposed) return;
        _isActive = false;
        CancelRoll();
        _disposed = true;
    }

    private void CancelRoll()
    {
        var cts = _rollCts;
        _rollCts = null;
        if (cts == null) return;

        try { cts.Cancel(); } catch { }
        cts.Dispose();
    }

    private void CbFaces_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == System.Windows.Input.Key.Enter)
        {
            Config_Changed(sender, e);
        }
    }

    private int ParseFaces()
    {
        if (CbFaces == null) return 6;
        string text = CbFaces.Text?.Trim() ?? "";
        var match = System.Text.RegularExpressions.Regex.Match(text, @"\d+");
        if (match.Success && int.TryParse(match.Value, out int face) && face >= 2 && face <= 1000)
        {
            return face;
        }
        return CbFaces.SelectedIndex switch
        {
            1 => 4,
            2 => 8,
            3 => 10,
            4 => 12,
            5 => 20,
            6 => 100,
            _ => 6
        };
    }

    private void Config_Changed(object sender, RoutedEventArgs e)
    {
        if (!_isReady || Rb2Dice == null || CbFaces == null) return;

        _diceCount = Rb2Dice.IsChecked == true ? 2 : 1;
        _maxFace = ParseFaces();

        UpdateDisplay(_maxFace, _diceCount == 2 ? _maxFace : null);
        UpdateStatsTable();
    }

    private async void BtnRoll_Click(object sender, RoutedEventArgs e)
    {
        if (_isRolling || !_isActive || _disposed) return;

        CancelRoll();
        _rollCts = new CancellationTokenSource();
        var token = _rollCts.Token;

        _isRolling = true;
        BtnRoll.IsEnabled = false;

        try
        {
            var rng = new Random();
            for (int step = 0; step < 10; step++)
            {
                token.ThrowIfCancellationRequested();
                int r1 = rng.Next(1, _maxFace + 1);
                int? r2 = _diceCount == 2 ? rng.Next(1, _maxFace + 1) : null;
                UpdateDisplay(r1, r2);
                await Task.Delay(40 + step * 8, token);
            }

            token.ThrowIfCancellationRequested();
            if (_disposed || !_isActive) return;

            int final1 = rng.Next(1, _maxFace + 1);
            int? final2 = _diceCount == 2 ? rng.Next(1, _maxFace + 1) : null;
            UpdateDisplay(final1, final2);

            _faceCounts[final1] = _faceCounts.GetValueOrDefault(final1, 0) + 1;
            _totalThrows++;
            if (final2.HasValue)
            {
                _faceCounts[final2.Value] = _faceCounts.GetValueOrDefault(final2.Value, 0) + 1;
                _totalThrows++;
            }

            UpdateStatsTable();
            _soundService?.PlayChime();
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Normal lifecycle cancellation.
        }
        finally
        {
            _isRolling = false;
            if (!_disposed && BtnRoll != null)
            {
                BtnRoll.IsEnabled = true;
            }
        }
    }

    private void UpdateDisplay(int v1, int? v2)
    {
        if (TxtDiceSymbol == null || TxtDiceValue == null) return;

        if (_maxFace == 6 && DiceChars.ContainsKey(v1) && (!v2.HasValue || DiceChars.ContainsKey(v2.Value)))
        {
            TxtDiceSymbol.FontFamily = new System.Windows.Media.FontFamily("Segoe UI Symbol");
            TxtDiceSymbol.FontSize = v2.HasValue ? 34 : 44;
            TxtDiceSymbol.Text = v2.HasValue ? $"{DiceChars[v1]} {DiceChars[v2.Value]}" : DiceChars[v1];
            TxtDiceValue.Text = v2.HasValue ? $"A={v1}, B={v2.Value} (합={v1 + v2.Value})" : $"결과: {v1}";
        }
        else
        {
            TxtDiceSymbol.FontFamily = new System.Windows.Media.FontFamily("Consolas");
            TxtDiceSymbol.FontSize = 32;
            TxtDiceSymbol.Text = v2.HasValue ? $"{v1}+{v2.Value}" : $"{v1}";
            TxtDiceValue.Text = v2.HasValue ? $"합계: {v1 + v2.Value}" : $"D{_maxFace}: {v1}";
        }
    }

    private void UpdateStatsTable()
    {
        if (ListStats == null) return;

        var rows = new List<DiceStatRow>();
        int limit = Math.Min(_maxFace, 20);

        for (int face = 1; face <= limit; face++)
        {
            int cnt = _faceCounts.GetValueOrDefault(face, 0);
            double ratio = _totalThrows > 0 ? (double)cnt / _totalThrows : 0.0;
            double pct = ratio * 100;

            rows.Add(new DiceStatRow
            {
                Face = face,
                Count = cnt,
                RatioStr = ratio.ToString("F3"),
                PercentStr = $"{pct:F1}%"
            });
        }

        ListStats.ItemsSource = rows;
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        CancelRoll();
        _isRolling = false;
        if (BtnRoll != null) BtnRoll.IsEnabled = true;
        _faceCounts.Clear();
        _totalThrows = 0;
        UpdateStatsTable();
        UpdateDisplay(6, _diceCount == 2 ? 6 : null);
    }
}
