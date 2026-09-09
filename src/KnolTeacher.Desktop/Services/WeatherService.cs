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
    IReadOnlyList<RegionCoordinate> DetailedCityCoordinates { get; }
    Task<WeatherAirQualityInfo?> GetWeatherAndAirQualityAsync(string? regionNameOrOfficeCode = null);
    RegionCoordinate ResolveSchoolRegion();
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

    public IReadOnlyList<RegionCoordinate> DetailedCityCoordinates { get; } = new List<RegionCoordinate>
    {
        // 강원특별자치도 (영동/영서 분리 정밀 기상)
        new("강릉", "K10", 37.7519, 128.8760),
        new("원주", "K10", 37.3422, 127.9202),
        new("춘천", "K10", 37.8813, 127.7298),
        new("속초", "K10", 38.2070, 128.5918),
        new("동해", "K10", 37.5247, 129.1143),
        new("삼척", "K10", 37.4499, 129.1653),
        new("태백", "K10", 37.1641, 128.9856),
        new("홍천", "K10", 37.6972, 127.8887),
        new("횡성", "K10", 37.4916, 127.9850),
        new("영월", "K10", 37.1836, 128.4619),
        new("평창", "K10", 37.3705, 128.3904),
        new("정선", "K10", 37.3806, 128.6608),
        new("철원", "K10", 38.1468, 127.3134),
        new("화천", "K10", 38.1062, 127.7082),
        new("양구", "K10", 38.1107, 127.9897),
        new("인제", "K10", 38.0697, 128.1704),
        new("고성", "K10", 38.3806, 128.4678),
        new("양양", "K10", 38.0754, 128.6189),

        // 경기도
        new("수원", "J10", 37.2636, 127.0286),
        new("성남", "J10", 37.4200, 127.1265),
        new("고양", "J10", 37.6584, 126.8320),
        new("일산", "J10", 37.6584, 126.8320),
        new("용인", "J10", 37.2411, 127.1776),
        new("부천", "J10", 37.5034, 126.7660),
        new("안산", "J10", 37.3219, 126.8309),
        new("안양", "J10", 37.3943, 126.9568),
        new("남양주", "J10", 37.6360, 127.2165),
        new("화성", "J10", 37.1995, 126.8315),
        new("동탄", "J10", 37.2003, 127.0700),
        new("평택", "J10", 36.9921, 127.1129),
        new("의정부", "J10", 37.7381, 127.0337),
        new("시흥", "J10", 37.3802, 126.8029),
        new("파주", "J10", 37.7600, 126.7799),
        new("김포", "J10", 37.6152, 126.7157),
        new("광명", "J10", 37.4786, 126.8646),
        new("군포", "J10", 37.3614, 126.9352),
        new("이천", "J10", 37.2723, 127.4428),
        new("오산", "J10", 37.1498, 127.0772),
        new("하남", "J10", 37.5393, 127.2148),
        new("양주", "J10", 37.7853, 127.0458),
        new("구리", "J10", 37.5943, 127.1296),
        new("안성", "J10", 37.0080, 127.2798),
        new("포천", "J10", 37.8949, 127.2003),
        new("의왕", "J10", 37.3448, 126.9683),
        new("여주", "J10", 37.2984, 127.6371),
        new("동두천", "J10", 37.9036, 127.0607),
        new("과천", "J10", 37.4292, 126.9876),
        new("가평", "J10", 37.8314, 127.5097),
        new("양평", "J10", 37.4918, 127.4876),
        new("연천", "J10", 38.0964, 127.0749),

        // 충청북도 / 충청남도 / 대전 / 세종
        new("청주", "M10", 36.6424, 127.4890),
        new("충주", "M10", 36.9910, 127.9259),
        new("제천", "M10", 37.1326, 128.2117),
        new("천안", "N10", 36.8151, 127.1139),
        new("공주", "N10", 36.4465, 127.1190),
        new("보령", "N10", 36.3330, 126.6128),
        new("아산", "N10", 36.7898, 127.0018),
        new("서산", "N10", 36.7845, 126.4503),
        new("논산", "N10", 36.1872, 127.0987),
        new("당진", "N10", 36.8898, 126.6459),
        new("홍성", "N10", 36.6013, 126.6608),
        new("예산", "N10", 36.6806, 126.8453),
        new("태안", "N10", 36.7540, 126.2974),

        // 전북 / 전남 / 광주
        new("전주", "P10", 35.8242, 127.1480),
        new("익산", "P10", 35.9483, 126.9576),
        new("군산", "P10", 35.9676, 126.7366),
        new("정읍", "P10", 35.5699, 126.8576),
        new("남원", "P10", 35.4164, 127.3904),
        new("김제", "P10", 35.8036, 126.8808),
        new("목포", "Q10", 34.8118, 126.3922),
        new("여수", "Q10", 34.7604, 127.6622),
        new("순천", "Q10", 34.9506, 127.4872),
        new("나주", "Q10", 35.0161, 126.7108),
        new("광양", "Q10", 34.9407, 127.6959),
        new("해남", "Q10", 34.5735, 126.5991),
        new("완도", "Q10", 34.3111, 126.7550),

        // 경북 / 경남 / 대구 / 부산 / 울산
        new("포항", "R10", 36.0190, 129.3435),
        new("경주", "R10", 35.8562, 129.2247),
        new("김천", "R10", 36.1398, 128.1136),
        new("안동", "R10", 36.5684, 128.7294),
        new("구미", "R10", 36.1195, 128.3446),
        new("영주", "R10", 36.8057, 128.6241),
        new("영천", "R10", 35.9733, 128.9386),
        new("상주", "R10", 36.4109, 128.1591),
        new("문경", "R10", 36.5938, 128.1866),
        new("경산", "R10", 35.8251, 128.7414),
        new("창원", "S10", 35.2280, 128.6811),
        new("진주", "S10", 35.1802, 128.1076),
        new("통영", "S10", 34.8544, 128.4332),
        new("사천", "S10", 35.0036, 128.0645),
        new("김해", "S10", 35.2285, 128.8894),
        new("밀양", "S10", 35.5038, 128.7466),
        new("거제", "S10", 34.8806, 128.6211),
        new("양산", "S10", 35.3350, 129.0373),

        // 제주특별자치도
        new("제주시", "T10", 33.4996, 126.5312),
        new("서귀포", "T10", 33.2541, 126.5601)
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

    public RegionCoordinate ResolveSchoolRegion()
    {
        var cfg = _configService.NeisConfig;

        // 1. Check SchoolName (e.g. "강릉교동초등학교" -> "강릉")
        if (!string.IsNullOrEmpty(cfg.SchoolName))
        {
            var match = DetailedCityCoordinates.FirstOrDefault(c => cfg.SchoolName.Contains(c.Name));
            if (match != null) return match;
        }

        // 2. Check SchoolAddress (e.g. "강원특별자치도 강릉시 하슬라로..." -> "강릉")
        if (!string.IsNullOrEmpty(cfg.SchoolAddress))
        {
            var match = DetailedCityCoordinates.FirstOrDefault(c => cfg.SchoolAddress.Contains(c.Name));
            if (match != null) return match;
        }

        // 3. Check LocationName or OfficeName
        string loc = $"{cfg.LocationName} {cfg.OfficeName}";
        if (!string.IsNullOrWhiteSpace(loc))
        {
            var cityMatch = DetailedCityCoordinates.FirstOrDefault(c => loc.Contains(c.Name));
            if (cityMatch != null) return cityMatch;

            var provMatch = SupportedRegions.FirstOrDefault(r => loc.Contains(r.Name));
            if (provMatch != null) return provMatch;
        }

        // 4. Check OfficeCode
        if (!string.IsNullOrEmpty(cfg.OfficeCode))
        {
            var match = SupportedRegions.FirstOrDefault(r => r.OfficeCode.Equals(cfg.OfficeCode, StringComparison.OrdinalIgnoreCase));
            if (match != null) return match;
        }

        return SupportedRegions[0]; // 서울
    }

    private RegionCoordinate ResolveRegion(string? input)
    {
        if (!string.IsNullOrEmpty(input))
        {
            // Remove "(우리학교)" or emoji if present in UI string
            string clean = input.Replace("🏫", "").Replace("(우리학교)", "").Trim();

            // Match detailed city first
            var cityMatch = DetailedCityCoordinates.FirstOrDefault(c => c.Name.Equals(clean, StringComparison.OrdinalIgnoreCase) || clean.Contains(c.Name));
            if (cityMatch != null) return cityMatch;

            // Match supported regions
            var match = SupportedRegions.FirstOrDefault(r => r.Name.Contains(clean) || clean.Contains(r.Name) || r.OfficeCode.Equals(clean, StringComparison.OrdinalIgnoreCase));
            if (match != null) return match;
        }

        return ResolveSchoolRegion();
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
