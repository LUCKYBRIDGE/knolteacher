using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MealWidgetView : UserControl
{
    private readonly INeisService? _neisService;
    private DateTime _currentDate = DateTime.Today;

    public MealWidgetView(INeisService? neisService = null)
    {
        _neisService = neisService;
        InitializeComponent();
        Loaded += async (s, e) => await LoadMealForDateAsync(_currentDate);
    }

    private async Task LoadMealForDateAsync(DateTime date)
    {
        _currentDate = date;
        UpdateDateHeader();

        if (_neisService != null)
        {
            TxtMeal.Text = "급식 메뉴 불러오는 중...";
            TxtCalorie.Text = "열량 계산 중";

            try
            {
                var meal = await _neisService.GetMealAsync(date);
                if (meal != null && !string.IsNullOrWhiteSpace(meal.MenuText))
                {
                    TxtMeal.Text = meal.MenuText;
                    TxtCalorie.Text = string.IsNullOrEmpty(meal.Calorie) ? "열량 정보 없음" : meal.Calorie;
                }
                else
                {
                    TxtMeal.Text = "등록된 급식 식단이 없습니다.\n(방학, 휴업일 또는 미등록)";
                    TxtCalorie.Text = "- kcal";
                }
            }
            catch
            {
                TxtMeal.Text = "급식 정보를 가져올 수 없습니다.\n인터넷 연결 또는 학교 설정을 확인해 주세요.";
                TxtCalorie.Text = "- kcal";
            }
        }
    }

    private void UpdateDateHeader()
    {
        bool isToday = _currentDate.Date == DateTime.Today;
        string dayOfWeek = _currentDate.ToString("ddd");
        string label = isToday 
            ? $"오늘 ({_currentDate:M.d} {dayOfWeek})" 
            : $"{_currentDate:M.d} ({dayOfWeek})";
        TxtMealDate.Text = label;
    }

    private async void BtnPrevMeal_Click(object sender, RoutedEventArgs e)
    {
        await LoadMealForDateAsync(_currentDate.AddDays(-1));
    }

    private async void BtnNextMeal_Click(object sender, RoutedEventArgs e)
    {
        await LoadMealForDateAsync(_currentDate.AddDays(1));
    }

    private async void BtnTodayMeal_Click(object sender, RoutedEventArgs e)
    {
        await LoadMealForDateAsync(DateTime.Today);
    }
}
