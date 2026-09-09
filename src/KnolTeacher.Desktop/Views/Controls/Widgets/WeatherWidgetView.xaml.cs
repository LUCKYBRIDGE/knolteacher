using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class WeatherWidgetView : UserControl, IWidgetLifecycle
{
    private readonly IWeatherService _weatherService;
    private CancellationTokenSource? _refreshCts;
    private bool _isInitialized = false;
    private bool _isActive = false;
    private bool _disposed = false;

    public WeatherWidgetView(IWeatherService? weatherService = null)
    {
        _weatherService = weatherService ?? ((Application.Current as App)?.Services?.GetService(typeof(IWeatherService)) as IWeatherService)!;
        InitializeComponent();
    }

    public void Activate()
    {
        if (_disposed || _isActive) return;

        _isActive = true;
        if (!_isInitialized)
        {
            InitRegions();
            _isInitialized = true;
        }

        _ = BeginRefreshAsync();
    }

    public void Deactivate()
    {
        if (_disposed || !_isActive) return;

        _isActive = false;
        CancelRefresh();
    }

    public void Dispose()
    {
        if (_disposed) return;

        Deactivate();
        CancelRefresh();
        _disposed = true;
    }

    private void InitRegions()
    {
        try
        {
            CbRegion.Items.Clear();

            var schoolRegion = _weatherService.ResolveSchoolRegion();
            string schoolTag = $"🏫 {schoolRegion.Name} (우리학교)";
            CbRegion.Items.Add(schoolTag);

            if (_weatherService is WeatherService concreteService)
            {
                var localCities = concreteService.DetailedCityCoordinates
                    .Where(c => c.OfficeCode == schoolRegion.OfficeCode && c.Name != schoolRegion.Name)
                    .OrderBy(c => c.Name)
                    .ToList();
                foreach (var c in localCities)
                {
                    CbRegion.Items.Add(c.Name);
                }

                foreach (var r in concreteService.SupportedRegions)
                {
                    if (r.Name != schoolRegion.Name)
                    {
                        CbRegion.Items.Add(r.Name);
                    }
                }
            }

            CbRegion.SelectedIndex = 0;
        }
        catch { }
    }

    private async Task BeginRefreshAsync()
    {
        if (_disposed || !_isActive) return;

        CancelRefresh();
        _refreshCts = new CancellationTokenSource();
        var token = _refreshCts.Token;

        try
        {
            await RefreshWeatherAsync(token);
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Hidden/closed widgets must not apply stale async results.
        }
    }

    private async Task RefreshWeatherAsync(CancellationToken cancellationToken)
    {
        try
        {
            string selRegion = CbRegion.SelectedItem as string ?? "서울";
            var weatherTask = _weatherService.GetWeatherAndAirQualityAsync(selRegion);
            var w = await weatherTask.WaitAsync(cancellationToken);

            cancellationToken.ThrowIfCancellationRequested();
            if (_disposed || !_isActive || w == null) return;

            TxtWeatherIcon.Text = w.WeatherIcon;
            TxtTemperature.Text = $"{w.Temperature:0.0}°C";
            TxtWeatherDesc.Text = $"{w.WeatherDescription} (체감 {w.ApparentTemperature:0.0}°C)";
            TxtHumidity.Text = $"💧 습도 {w.Humidity}%";
            TxtWind.Text = $"💨 풍속 {w.WindSpeed:0.0}m/s";

            TxtPm10.Text = $"{w.Pm10Grade} ({w.Pm10:0}µg)";
            BdPm10.Background = (Brush)new BrushConverter().ConvertFromString(w.Pm10BadgeBg)!;
            TxtPm10.Foreground = (Brush)new BrushConverter().ConvertFromString(w.Pm10BadgeFg)!;

            TxtPm25.Text = $"{w.Pm25Grade} ({w.Pm25:0}µg)";
            BdPm25.Background = (Brush)new BrushConverter().ConvertFromString(w.Pm25BadgeBg)!;
            TxtPm25.Foreground = (Brush)new BrushConverter().ConvertFromString(w.Pm25BadgeFg)!;

            TxtOutdoorGuide.Text = w.OutdoorActivityGuide;
            BdOutdoorGuide.Background = (Brush)new BrushConverter().ConvertFromString(w.OutdoorGuideBg)!;
            TxtOutdoorGuide.Foreground = (Brush)new BrushConverter().ConvertFromString(w.OutdoorGuideFg)!;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            // Existing widget behavior intentionally treats weather failures as non-fatal.
        }
    }

    private void CancelRefresh()
    {
        var cts = _refreshCts;
        _refreshCts = null;
        if (cts == null) return;

        try { cts.Cancel(); } catch { }
        cts.Dispose();
    }

    private async void CbRegion_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_isInitialized && _isActive && !_disposed)
        {
            await BeginRefreshAsync();
        }
    }

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
    {
        if (_isActive && !_disposed)
        {
            await BeginRefreshAsync();
        }
    }
}
