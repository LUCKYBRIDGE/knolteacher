using System;

namespace KnolTeacher.Desktop.Models;

public class WeatherAirQualityInfo
{
    public string RegionName { get; set; } = "서울";
    public double Latitude { get; set; } = 37.5665;
    public double Longitude { get; set; } = 126.9780;

    public double Temperature { get; set; }
    public double ApparentTemperature { get; set; }
    public int Humidity { get; set; }
    public double WindSpeed { get; set; }
    public int WeatherCode { get; set; }
    public string WeatherDescription { get; set; } = "맑음";
    public string WeatherIcon { get; set; } = "☀️";

    public double Pm10 { get; set; }
    public string Pm10Grade { get; set; } = "좋음";
    public string Pm10BadgeBg { get; set; } = "#DCFCE7";
    public string Pm10BadgeFg { get; set; } = "#166534";

    public double Pm25 { get; set; }
    public string Pm25Grade { get; set; } = "좋음";
    public string Pm25BadgeBg { get; set; } = "#DCFCE7";
    public string Pm25BadgeFg { get; set; } = "#166534";

    // Ministry of Education Outdoor Activity Safety Guide
    public string OutdoorActivityGuide { get; set; } = "🏃 실외활동 및 체육수업 정상 가능";
    public string OutdoorGuideBg { get; set; } = "#DCFCE7";
    public string OutdoorGuideFg { get; set; } = "#166534";

    public string UpdatedTime { get; set; } = DateTime.Now.ToString("HH:mm");
}

public record RegionCoordinate(string Name, string OfficeCode, double Lat, double Lon);
