using System;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class WeatherWidgetView : UserControl
{
    private readonly IWeatherService _weatherService;
    private bool _isInitialized = false;

    public WeatherWidgetView(IWeatherService? weatherService = null)
    {
        _weatherService = weatherService ?? ((Application.Current as App)?.Services?.GetService(typeof(IWeatherService)) as IWeatherService)!;
        InitializeComponent();

        Loaded += async (s, e) =>
        {
            if (!_isInitialized)
            {
                InitRegions();
                _isInitialized = true;
                await RefreshWeatherAsync();
            }
        };
    }

    private void InitRegions()
    {
        try
        {
            CbRegion.Items.Clear();

            // 1. School local region
            var schoolRegion = _weatherService.ResolveSchoolRegion();
            string schoolTag = $"🏫 {schoolRegion.Name} (우리학교)";
            CbRegion.Items.Add(schoolTag);

            // 2. Local cities in same province
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

                // 3. Other provinces
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

    private async Task RefreshWeatherAsync()
    {
        try
        {
            string selRegion = CbRegion.SelectedItem as string ?? "서울";
            var w = await _weatherService.GetWeatherAndAirQualityAsync(selRegion);
            if (w != null)
            {
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
        }
        catch { }
    }

    private async void CbRegion_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_isInitialized)
        {
            await RefreshWeatherAsync();
        }
    }

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
    {
        await RefreshWeatherAsync();
    }
}
