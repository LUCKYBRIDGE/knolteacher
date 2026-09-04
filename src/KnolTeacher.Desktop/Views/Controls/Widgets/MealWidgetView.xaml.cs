using System;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MealWidgetView : UserControl
{
    private readonly INeisService? _neisService;

    public MealWidgetView(INeisService? neisService = null)
    {
        _neisService = neisService;
        InitializeComponent();
        Loaded += async (s, e) =>
        {
            if (_neisService != null)
            {
                var meal = await _neisService.GetMealAsync();
                if (meal != null)
                {
                    TxtMeal.Text = string.IsNullOrEmpty(meal.MenuText) ? "오늘 등록된 급식이 없습니다." : meal.MenuText;
                    TxtCalorie.Text = string.IsNullOrEmpty(meal.Calorie) ? "열량: 정보 없음" : $"열량: {meal.Calorie}";
                }
                else
                {
                    TxtMeal.Text = "급식 정보를 가져올 수 없습니다.";
                    TxtCalorie.Text = "열량: 정보 없음";
                }
            }
        };
    }
}
