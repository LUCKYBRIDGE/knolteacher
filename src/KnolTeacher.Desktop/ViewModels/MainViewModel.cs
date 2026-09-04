using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly IConfigService _configService;

    [ObservableProperty]
    private string _appTitle = "놀티쳐 (KnolTeacher) .NET";

    [ObservableProperty]
    private string _schoolName = "학교 설정 필요";

    [ObservableProperty]
    private string _gradeClassInfo = "5학년 2반";

    [ObservableProperty]
    private string _currentTimeString = string.Empty;

    public MainViewModel(IConfigService configService)
    {
        _configService = configService;
        UpdateHeaderInfo();
    }

    public void UpdateHeaderInfo()
    {
        if (!string.IsNullOrWhiteSpace(_configService.NeisConfig.SchoolName))
        {
            SchoolName = _configService.NeisConfig.SchoolName;
            GradeClassInfo = $"{_configService.NeisConfig.Grade}학년 {_configService.NeisConfig.ClassName}반";
        }
    }
}
