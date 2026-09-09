using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MealWidgetView : UserControl, IWidgetLifecycle
{
    private readonly INeisService? _neisService;
    private CancellationTokenSource? _loadCts;
    private DateTime _currentDate = DateTime.Today;
    private bool _isActive = false;
    private bool _disposed = false;

    public MealWidgetView(INeisService? neisService = null)
    {
        _neisService = neisService;
        InitializeComponent();
    }

    public void Activate()
    {
        if (_disposed || _isActive) return;
        _isActive = true;
        _ = BeginLoadMealAsync(_currentDate);
    }

    public void Deactivate()
    {
        if (_disposed || !_isActive) return;
        _isActive = false;
        CancelLoad();
    }

    public void Dispose()
    {
        if (_disposed) return;
        Deactivate();
        CancelLoad();
        _disposed = true;
    }

    private async Task BeginLoadMealAsync(DateTime date)
    {
        if (_disposed || !_isActive) return;

        CancelLoad();
        _loadCts = new CancellationTokenSource();
        var token = _loadCts.Token;

        try
        {
            await LoadMealForDateAsync(date, token);
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Hidden/closed widgets must not apply stale results.
        }
    }

    private async Task LoadMealForDateAsync(DateTime date, CancellationToken cancellationToken)
    {
        _currentDate = date;
        UpdateDateHeader();

        if (_neisService == null) return;

        TxtMeal.Text = "급식 메뉴 불러오는 중...";
        TxtCalorie.Text = "열량 계산 중";

        try
        {
            var mealTask = _neisService.GetMealAsync(date);
            var meal = await mealTask.WaitAsync(cancellationToken);
            cancellationToken.ThrowIfCancellationRequested();
            if (_disposed || !_isActive) return;

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
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            if (_disposed || !_isActive) return;
            TxtMeal.Text = "급식 정보를 가져올 수 없습니다.\n인터넷 연결 또는 학교 설정을 확인해 주세요.";
            TxtCalorie.Text = "- kcal";
        }
    }

    private void CancelLoad()
    {
        var cts = _loadCts;
        _loadCts = null;
        if (cts == null) return;

        try { cts.Cancel(); } catch { }
        cts.Dispose();
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
        await BeginLoadMealAsync(_currentDate.AddDays(-1));
    }

    private async void BtnNextMeal_Click(object sender, RoutedEventArgs e)
    {
        await BeginLoadMealAsync(_currentDate.AddDays(1));
    }

    private async void BtnTodayMeal_Click(object sender, RoutedEventArgs e)
    {
        await BeginLoadMealAsync(DateTime.Today);
    }
}
