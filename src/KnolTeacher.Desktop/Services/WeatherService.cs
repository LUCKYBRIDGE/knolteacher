using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IWeatherService
{
    IReadOnlyList<RegionCoordinate> SupportedRegions { get; }
    Task<WeatherAirQualityInfo?> GetWeatherAndAirQualityAsync(string? regionNameOrOfficeCode = null);
}

public class WeatherService : IWeatherService
{
    private readonly IConfigService _configService;
    private static readonly HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(6)
    };

    private WeatherAirQualityInfo? _cachedInfo;
    private DateTime _cacheTime = DateTime.MinValue;
    private string _cachedRegion = string.Empty;

    public IReadOnlyList<RegionCoordinate> SupportedRegions { get; } = new List<RegionCoordinate>
    {
        new("서울", "B10", 37.5665, 126.9780),
        new("경기", "J10", 37.2636, 127.0286),
        new("인천", "E10", 37.4563, 126.7052),
        new("부산", "C10", 35.1796, 129.0756),
        new("대구", "D10", 35.8714, 128.6014),
        new("광주", "F10", 35.1595, 126.8526),
        new("대전", "G10", 36.3504, 127.3845),
        new("울산", "H10", 35.5384, 129.3114),
        new("세종", "I10", 36.4800, 127.2890),
        new("강원", "K10", 37.8813, 127.7298),
        new("충북", "M10", 36.6424, 127.4890),
        new("충남", "N10", 36.6013, 126.6608),
        new("전북", "P10", 35.8242, 127.1480),
        new("전남", "Q10", 34.9904, 126.4817),
        new("경북", "R10", 36.5684, 128.7294),
        new("경남", "S10", 35.2280, 128.6811),
        new("제주", "T10", 33.4996, 126.5312)
    };

    public WeatherService(IConfigService configService)
    {
        _configService = configService;
    }

    public async Task<WeatherAirQualityInfo?> GetWeatherAndAirQualityAsync(string? regionNameOrOfficeCode = null)
    {
        var targetRegion = ResolveRegion(regionNameOrOfficeCode);

        // Check 15-min cache
        if (_cachedInfo != null && _cachedRegion == targetRegion.Name && (DateTime.Now - _cacheTime).TotalMinutes < 15)
        {
            return _cachedInfo;
        }

        try
        {
            // 1. Weather Forecast
            string weatherUrl = $"https://api.open-meteo.com/v1/forecast?latitude={targetRegion.Lat}&longitude={targetRegion.Lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&timezone=Asia%2FSeoul";
            string airUrl = $"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={targetRegion.Lat}&longitude={targetRegion.Lon}&current=pm10,pm2_5&timezone=Asia%2FSeoul";

            var weatherTask = _httpClient.GetStringAsync(weatherUrl);
            var airTask = _httpClient.GetStringAsync(airUrl);

            await Task.WhenAll(weatherTask, airTask);

            using var weatherDoc = JsonDocument.Parse(await weatherTask);
            using var airDoc = JsonDocument.Parse(await airTask);

            var wCur = weatherDoc.RootElement.GetProperty("current");
            var aCur = airDoc.RootElement.GetProperty("current");

            double temp = wCur.GetProperty("temperature_2m").GetDouble();
            double appTemp = wCur.GetProperty("apparent_temperature").GetDouble();
            int humidity = (int)wCur.GetProperty("relative_humidity_2m").GetDouble();
            double wind = wCur.GetProperty("wind_speed_10m").GetDouble();
            int code = wCur.GetProperty("weather_code").GetInt32();

            double pm10 = aCur.GetProperty("pm10").GetDouble();
            double pm25 = aCur.GetProperty("pm2_5").GetDouble();

            var (desc, icon) = MapWeatherCode(code);

            var info = new WeatherAirQualityInfo
            {
                RegionName = targetRegion.Name,
                Latitude = targetRegion.Lat,
                Longitude = targetRegion.Lon,
                Temperature = temp,
                ApparentTemperature = appTemp,
                Humidity = humidity,
                WindSpeed = wind,
                WeatherCode = code,
                WeatherDescription = desc,
                WeatherIcon = icon,
                Pm10 = pm10,
                Pm25 = pm25,
                UpdatedTime = DateTime.Now.ToString("HH:mm")
            };

            // Grade PM10 & PM2.5 based on Korean Ministry of Environment criteria
            GradeAirQuality(info);

            _cachedInfo = info;
            _cachedRegion = targetRegion.Name;
            _cacheTime = DateTime.Now;

            return info;
        }
        catch (Exception ex)
        {
            App.BootLog($"[WeatherService] Error: {ex.Message}");
            return _cachedInfo;
        }
    }

    private RegionCoordinate ResolveRegion(string? input)
    {
        if (!string.IsNullOrEmpty(input))
        {
            var match = SupportedRegions.FirstOrDefault(r => r.Name.Contains(input) || input.Contains(r.Name) || r.OfficeCode.Equals(input, StringComparison.OrdinalIgnoreCase));
            if (match != null) return match;
        }

        // Fallback to user config's office code
        var cfg = _configService.NeisConfig;
        if (!string.IsNullOrEmpty(cfg.OfficeCode))
        {
            var match = SupportedRegions.FirstOrDefault(r => r.OfficeCode.Equals(cfg.OfficeCode, StringComparison.OrdinalIgnoreCase));
            if (match != null) return match;
        }
        if (!string.IsNullOrEmpty(cfg.OfficeName))
        {
            var match = SupportedRegions.FirstOrDefault(r => cfg.OfficeName.Contains(r.Name));
            if (match != null) return match;
        }

        // Default to Seoul
        return SupportedRegions[0];
    }

    private static (string Description, string Icon) MapWeatherCode(int code) => code switch
    {
        0 => ("맑음", "☀️"),
        1 => ("대체로 맑음", "🌤️"),
        2 => ("구름 조금", "⛅"),
        3 => ("흐림", "☁️"),
        45 or 48 => ("안개", "🌫️"),
        51 or 53 or 55 => ("이슬비", "🌦️"),
        61 or 63 or 65 => ("비", "🌧️"),
        71 or 73 or 75 => ("눈", "❄️"),
        77 => ("진눈깨비", "🌨️"),
        80 or 81 or 82 => ("소나기", "🌧️"),
        85 or 86 => ("눈보라", "🌨️"),
        95 or 96 or 99 => ("뇌우", "⛈️"),
        _ => ("구름", "⛅")
    };

    private static void GradeAirQuality(WeatherAirQualityInfo info)
    {
        // PM10 Korean criteria: 0~30 좋음, 31~80 보통, 81~150 나쁨, 151+ 매우나쁨
        if (info.Pm10 <= 30)
        {
            info.Pm10Grade = "좋음";
            info.Pm10BadgeBg = "#DCFCE7";
            info.Pm10BadgeFg = "#166534";
        }
        else if (info.Pm10 <= 80)
        {
            info.Pm10Grade = "보통";
            info.Pm10BadgeBg = "#E0E7FF";
            info.Pm10BadgeFg = "#3730A3";
        }
        else if (info.Pm10 <= 150)
        {
            info.Pm10Grade = "나쁨";
            info.Pm10BadgeBg = "#FEF3C7";
            info.Pm10BadgeFg = "#92400E";
        }
        else
        {
            info.Pm10Grade = "매우나쁨";
            info.Pm10BadgeBg = "#FEE2E2";
            info.Pm10BadgeFg = "#991B1B";
        }

        // PM2.5 Korean criteria: 0~15 좋음, 16~35 보통, 36~75 나쁨, 76+ 매우나쁨
        if (info.Pm25 <= 15)
        {
            info.Pm25Grade = "좋음";
            info.Pm25BadgeBg = "#DCFCE7";
            info.Pm25BadgeFg = "#166534";
        }
        else if (info.Pm25 <= 35)
        {
            info.Pm25Grade = "보통";
            info.Pm25BadgeBg = "#E0E7FF";
            info.Pm25BadgeFg = "#3730A3";
        }
        else if (info.Pm25 <= 75)
        {
            info.Pm25Grade = "나쁨";
            info.Pm25BadgeBg = "#FEF3C7";
            info.Pm25BadgeFg = "#92400E";
        }
        else
        {
            info.Pm25Grade = "매우나쁨";
            info.Pm25BadgeBg = "#FEE2E2";
            info.Pm25BadgeFg = "#991B1B";
        }

        // Ministry of Education Guideline (Takes worse of PM10 and PM2.5)
        bool isVeryBad = info.Pm10 > 150 || info.Pm25 > 75;
        bool isBad = info.Pm10 > 80 || info.Pm25 > 35;

        if (isVeryBad)
        {
            info.OutdoorActivityGuide = "🚫 실외수업 금지 (강당·체육관 대체)";
            info.OutdoorGuideBg = "#FEE2E2";
            info.OutdoorGuideFg = "#991B1B";
        }
        else if (isBad)
        {
            info.OutdoorActivityGuide = "😷 실외활동 자제 / 마스크 착용 권고";
            info.OutdoorGuideBg = "#FEF3C7";
            info.OutdoorGuideFg = "#92400E";
        }
        else
        {
            info.OutdoorActivityGuide = "🏃 실외활동 및 체육수업 정상 가능";
            info.OutdoorGuideBg = "#DCFCE7";
            info.OutdoorGuideFg = "#166534";
        }
    }
}
