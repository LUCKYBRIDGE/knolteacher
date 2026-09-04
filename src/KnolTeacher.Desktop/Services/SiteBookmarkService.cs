using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface ISiteBookmarkService
{
    List<SiteBookmarkItem> Bookmarks { get; }
    List<EducationOfficeItem> EducationOffices { get; }
    string SelectedRegionCode { get; set; }
    event Action? OnBookmarksChanged;

    void Load();
    void Save();
    void AddCustomSite(string title, string url, string desc, string icon);
    void RemoveBookmark(string id);
    void ResetToDefaults();
    void OpenSite(string url);
    void OpenSelectedOfficePortal();
}

public class SiteBookmarkService : ISiteBookmarkService
{
    private readonly IConfigService _configService;
    private readonly string _filePath;
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };

    public List<SiteBookmarkItem> Bookmarks { get; private set; } = new();
    public List<EducationOfficeItem> EducationOffices { get; } = new();
    public string SelectedRegionCode { get; set; } = "gwe"; // 기본 강원

    public event Action? OnBookmarksChanged;

    public SiteBookmarkService(IConfigService configService)
    {
        _configService = configService;
        _filePath = Path.Combine(_configService.ConfigDir, "site_bookmarks.json");

        InitEducationOffices();
        Load();
    }

    private void InitEducationOffices()
    {
        EducationOffices.Clear();
        EducationOffices.AddRange(new[]
        {
            new EducationOfficeItem { RegionName = "강원특별자치도", OfficeName = "강원교육청", DomainCode = "gwe" },
            new EducationOfficeItem { RegionName = "서울특별시", OfficeName = "서울교육청", DomainCode = "sen" },
            new EducationOfficeItem { RegionName = "경기도", OfficeName = "경기교육청", DomainCode = "goe" },
            new EducationOfficeItem { RegionName = "부산광역시", OfficeName = "부산교육청", DomainCode = "pen" },
            new EducationOfficeItem { RegionName = "대구광역시", OfficeName = "대구교육청", DomainCode = "dge" },
            new EducationOfficeItem { RegionName = "인천광역시", OfficeName = "인천교육청", DomainCode = "ice" },
            new EducationOfficeItem { RegionName = "광주광역시", OfficeName = "광주교육청", DomainCode = "gen" },
            new EducationOfficeItem { RegionName = "대전광역시", OfficeName = "대전교육청", DomainCode = "dje" },
            new EducationOfficeItem { RegionName = "울산광역시", OfficeName = "울산교육청", DomainCode = "use" },
            new EducationOfficeItem { RegionName = "세종특별자치시", OfficeName = "세종교육청", DomainCode = "sje" },
            new EducationOfficeItem { RegionName = "충청북도", OfficeName = "충북교육청", DomainCode = "cbe" },
            new EducationOfficeItem { RegionName = "충청남도", OfficeName = "충남교육청", DomainCode = "cne" },
            new EducationOfficeItem { RegionName = "전북특별자치도", OfficeName = "전북교육청", DomainCode = "jbe" },
            new EducationOfficeItem { RegionName = "전라남도", OfficeName = "전남교육청", DomainCode = "jne" },
            new EducationOfficeItem { RegionName = "경상북도", OfficeName = "경북교육청", DomainCode = "gbe" },
            new EducationOfficeItem { RegionName = "경상남도", OfficeName = "경남교육청", DomainCode = "gne" },
            new EducationOfficeItem { RegionName = "제주특별자치도", OfficeName = "제주교육청", DomainCode = "jje" }
        });
    }

    public void Load()
    {
        try
        {
            if (File.Exists(_filePath))
            {
                string json = File.ReadAllText(_filePath);
                var loaded = JsonSerializer.Deserialize<List<SiteBookmarkItem>>(json, _jsonOptions);
                if (loaded != null && loaded.Count > 0)
                {
                    Bookmarks = loaded;
                    LoadSavedRegion();
                    return;
                }
            }
        }
        catch { }

        ResetToDefaults();
        LoadSavedRegion();
    }

    private void LoadSavedRegion()
    {
        try
        {
            string regPath = Path.Combine(_configService.ConfigDir, "selected_region.txt");
            if (File.Exists(regPath))
            {
                string saved = File.ReadAllText(regPath).Trim();
                if (!string.IsNullOrEmpty(saved) && EducationOffices.Any(e => e.DomainCode == saved))
                {
                    SelectedRegionCode = saved;
                }
            }
        }
        catch { }
    }

    public void Save()
    {
        try
        {
            Directory.CreateDirectory(_configService.ConfigDir);
            string json = JsonSerializer.Serialize(Bookmarks, _jsonOptions);
            File.WriteAllText(_filePath, json);

            string regPath = Path.Combine(_configService.ConfigDir, "selected_region.txt");
            File.WriteAllText(regPath, SelectedRegionCode);
        }
        catch { }

        OnBookmarksChanged?.Invoke();
    }

    public void AddCustomSite(string title, string url, string desc, string icon)
    {
        if (string.IsNullOrWhiteSpace(title) || string.IsNullOrWhiteSpace(url)) return;

        if (!url.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
            !url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            url = "https://" + url;
        }

        var item = new SiteBookmarkItem
        {
            Id = Guid.NewGuid().ToString("N")[..8],
            Title = title.Trim(),
            Url = url.Trim(),
            Description = string.IsNullOrWhiteSpace(desc) ? "선생님 즐겨찾기" : desc.Trim(),
            Icon = string.IsNullOrWhiteSpace(icon) ? "⭐" : icon,
            Color = "#2563EB",
            Category = "사용자 추가",
            IsCustom = true
        };

        Bookmarks.Add(item);
        Save();
    }

    public void RemoveBookmark(string id)
    {
        var found = Bookmarks.FirstOrDefault(b => b.Id == id);
        if (found != null)
        {
            Bookmarks.Remove(found);
            Save();
        }
    }

    public void ResetToDefaults()
    {
        Bookmarks = new List<SiteBookmarkItem>
        {
            new() {
                Id = "pinky",
                Title = "핑키네 교실자료실",
                Description = "선생님을 위한 무료 학습지, 수업자료, 계절별 활동지 가득",
                Url = "https://pinky-ne.com/",
                Icon = "🌸",
                Color = "#EC4899",
                Category = "필수자료실",
                IsCustom = false
            },
            new() {
                Id = "knolquiz",
                Title = "놀퀴즈 (KnolQuiz)",
                Description = "학생 참여형 실시간 인터랙티브 퀴즈 and 게임",
                Url = "https://quiz.knolteacher.com/",
                Icon = "🎯",
                Color = "#3B82F6",
                Category = "수업도구",
                IsCustom = false
            },
            new() {
                Id = "iscream",
                Title = "아이스크림 (i-Scream)",
                Description = "초등 교과수업 및 창체자료 대표 교수학습 포털",
                Url = "https://www.i-scream.co.kr/",
                Icon = "🍦",
                Color = "#F59E0B",
                Category = "교수지원",
                IsCustom = false
            },
            new() {
                Id = "tsherpa",
                Title = "T셀파 (티셀파)",
                Description = "천재교육 교과서 수업자료 및 에듀테크 통합 지원",
                Url = "https://www.tsherpa.co.kr/",
                Icon = "🎒",
                Color = "#10B981",
                Category = "교수지원",
                IsCustom = false
            },
            new() {
                Id = "mteacher",
                Title = "M티처 (엠티처)",
                Description = "미래엔 교과서 풍부한 멀티미디어 디지털 수업자료",
                Url = "https://www.m-teacher.co.kr/",
                Icon = "📚",
                Color = "#6366F1",
                Category = "교수지원",
                IsCustom = false
            },
            new() {
                Id = "doclass",
                Title = "두클래스 (douclass)",
                Description = "동아출판 초등·중학 스마트 맞춤형 교수학습 지원",
                Url = "https://www.douclass.com/",
                Icon = "🏫",
                Color = "#8B5CF6",
                Category = "교수지원",
                IsCustom = false
            },
            new() {
                Id = "indischool",
                Title = "인디스쿨 (indischool)",
                Description = "대한민국 초등교사 커뮤니티 및 집단지성 수업자료 나눔",
                Url = "https://www.indischool.com/",
                Icon = "🍎",
                Color = "#EF4444",
                Category = "교사커뮤니티",
                IsCustom = false
            },
            new() {
                Id = "thinkerbell",
                Title = "띵커벨 (ThinkerBell)",
                Description = "쉽고 빠른 웹기반 퀴즈, 워크시트 및 보드 협업도구",
                Url = "https://www.tkbell.co.kr/",
                Icon = "🔔",
                Color = "#06B6D4",
                Category = "수업도구",
                IsCustom = false
            },
            new() {
                Id = "edunet",
                Title = "에듀넷 티-클리어",
                Description = "교육부·KERIS 국가 교육정보 및 교육과정 종합 포털",
                Url = "https://www.edunet.net/",
                Icon = "🏛️",
                Color = "#0284C7",
                Category = "국가교육",
                IsCustom = false
            },
            new() {
                Id = "miricanvas",
                Title = "미리캔버스 (교육용)",
                Description = "학교 프레젠테이션, 학습지, 카드뉴스 디자인 제작",
                Url = "https://www.miricanvas.com/",
                Icon = "🎨",
                Color = "#14B8A6",
                Category = "디자인도구",
                IsCustom = false
            },
            new() {
                Id = "canva",
                Title = "캔바 교사용 (Canva)",
                Description = "전 세계 1위 비주얼 교육자료 및 워크시트 템플릿",
                Url = "https://www.canva.com/ko_kr/education/",
                Icon = "✨",
                Color = "#00C4CC",
                Category = "디자인도구",
                IsCustom = false
            }
        };

        Save();
    }

    public void OpenSite(string url)
    {
        if (string.IsNullOrWhiteSpace(url)) return;

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true
            };
            Process.Start(psi);
        }
        catch { }
    }

    public void OpenSelectedOfficePortal()
    {
        var office = EducationOffices.FirstOrDefault(e => e.DomainCode == SelectedRegionCode)
                     ?? EducationOffices.FirstOrDefault();

        if (office != null)
        {
            OpenSite(office.Url);
        }
    }
}
