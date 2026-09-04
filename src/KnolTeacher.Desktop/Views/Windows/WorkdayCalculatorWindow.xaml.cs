using System;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class WorkdayCalculatorWindow : Window
{
    private readonly IWorkdayCalculatorService _calcService;
    private int _year = DateTime.Today.Year;
    private int _month = DateTime.Today.Month;
    private bool _isInitializing = true;

    private static readonly Brush BrushGreenBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DCFCE7"));
    private static readonly Brush BrushGreenBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#86EFAC"));
    private static readonly Brush BrushGreenText = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#166534"));

    private static readonly Brush BrushRedBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEE2E2"));
    private static readonly Brush BrushRedBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FCA5A5"));
    private static readonly Brush BrushRedText = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#991B1B"));

    public WorkdayCalculatorWindow(IWorkdayCalculatorService calcService)
    {
        InitializeComponent();
        _calcService = calcService;

        Closing += (s, e) =>
        {
            e.Cancel = true;
            Hide();
        };

        Loaded += WorkdayCalculatorWindow_Loaded;
    }

    private void WorkdayCalculatorWindow_Loaded(object sender, RoutedEventArgs e)
    {
        _isInitializing = true;
        _year = DateTime.Today.Year;
        _month = DateTime.Today.Month;
        UpdateMonthHeader();
        int holidays = _calcService.GetStandardHolidays(_year, _month);
        TbHolidays.Text = holidays.ToString();
        _isInitializing = false;
        Recalculate();
    }

    private void UpdateMonthHeader()
    {
        TxtCurrentYearMonth.Text = $"{_year}년 {_month:D2}월";
    }

    private void BtnPrevMonth_Click(object sender, RoutedEventArgs e)
    {
        _month--;
        if (_month < 1)
        {
            _month = 12;
            _year--;
        }
        UpdateMonthHeader();
        TbHolidays.Text = _calcService.GetStandardHolidays(_year, _month).ToString();
        Recalculate();
    }

    private void BtnNextMonth_Click(object sender, RoutedEventArgs e)
    {
        _month++;
        if (_month > 12)
        {
            _month = 1;
            _year++;
        }
        UpdateMonthHeader();
        TbHolidays.Text = _calcService.GetStandardHolidays(_year, _month).ToString();
        Recalculate();
    }

    private void Input_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (!_isInitializing)
        {
            Recalculate();
        }
    }

    private void Recalculate()
    {
        int holidays = int.TryParse(TbHolidays.Text, out int h) ? Math.Max(0, h) : 0;
        int vacations = int.TryParse(TbVacations.Text, out int v) ? Math.Max(0, v) : 0;
        int leaves = int.TryParse(TbLeaveDays.Text, out int l) ? Math.Max(0, l) : 0;
        int partialHours = int.TryParse(TbPartialHours.Text, out int p) ? Math.Max(0, p) : 0;

        var calc = _calcService.Calculate(_year, _month, holidays, vacations, leaves, partialHours);

        TxtTotalWeekdays.Text = $"{calc.TotalWeekdays} 일";
        TxtNetWorkdays.Text = calc.NetWorkdays.ToString();

        // Progress bar (target 15 out of ~21 max weekdays)
        double barMax = 260.0;
        double pct = Math.Min(1.2, (double)calc.NetWorkdays / 15.0);
        BarWorkdayProgress.Width = Math.Max(16.0, pct * (barMax * (15.0 / 20.0)));

        if (calc.IsEligible15Days)
        {
            BorderDecision.Background = BrushGreenBg;
            BorderDecision.BorderBrush = BrushGreenBorder;
            TxtDecisionTitle.Text = "🎉 15일 기준 달성! (수당 전액 100% 지급)";
            TxtDecisionTitle.Foreground = BrushGreenText;
            TxtDecisionSub.Text = "이번 달 실제 인정 출근일수가 15일 이상이므로 교직수당·정액급식비 등이 전액 지급됩니다.";
            TxtDecisionSub.Foreground = BrushGreenText;

            TxtUsableLeave.Text = calc.UsableLeaveWithoutDeduction > 0
                ? $"이번 달 최대 {calc.UsableLeaveWithoutDeduction}일 더 연가 사용 가능!"
                : "현재 15일 딱 맞춤 (추가 연가 사용 시 수당 차감)";
        }
        else
        {
            BorderDecision.Background = BrushRedBg;
            BorderDecision.BorderBrush = BrushRedBorder;
            int shortage = Math.Abs(calc.DaysDifferenceFrom15);
            TxtDecisionTitle.Text = $"⚠️ 15일 기준 미달! ({shortage}일 부족)";
            TxtDecisionTitle.Foreground = BrushRedText;
            TxtDecisionSub.Text = "이번 달 출근일수가 15일 미만이므로 정액급식비 및 시간외수당 정액분이 일할 차감됩니다.";
            TxtDecisionSub.Foreground = BrushRedText;

            TxtUsableLeave.Text = "출근일수 부족 상태 (추가 연가 시 차감폭 증가)";
        }

        // Summary breakdowns
        TxtSummaryTotal.Text = $"+{calc.TotalWeekdays}일";
        TxtSummaryHolidays.Text = $"-{calc.Holidays}일";
        TxtSummaryVacations.Text = $"-{calc.VacationDays}일";
        TxtSummaryLeave.Text = $"-{calc.LeaveDays}일";
        TxtSummaryPartial.Text = calc.PartialConvertedDays > 0
            ? $"-{calc.PartialConvertedDays}일 (누적 {calc.PartialHours}시간 중 {calc.PartialRemainingHours}시간 잔여)"
            : $"-0일 ({calc.PartialHours}시간 잔여, 8시간 미만)";

        TxtSummaryFinal.Text = calc.IsEligible15Days
            ? $"= {calc.NetWorkdays}일 (충족)"
            : $"= {calc.NetWorkdays}일 (미달)";
    }

    private void BtnCopyReport_Click(object sender, RoutedEventArgs e)
    {
        int holidays = int.TryParse(TbHolidays.Text, out int h) ? Math.Max(0, h) : 0;
        int vacations = int.TryParse(TbVacations.Text, out int v) ? Math.Max(0, v) : 0;
        int leaves = int.TryParse(TbLeaveDays.Text, out int l) ? Math.Max(0, l) : 0;
        int partialHours = int.TryParse(TbPartialHours.Text, out int p) ? Math.Max(0, p) : 0;

        var calc = _calcService.Calculate(_year, _month, holidays, vacations, leaves, partialHours);

        var sb = new StringBuilder();
        sb.AppendLine($"[교원 {_year}년 {_month:D2}월 복무 및 15일 출근일수 정산표]");
        sb.AppendLine($"- 총 평일(월~금): {calc.TotalWeekdays}일");
        sb.AppendLine($"- 법정 공휴일: -{calc.Holidays}일");
        sb.AppendLine($"- 방학/재량휴업일: -{calc.VacationDays}일");
        sb.AppendLine($"- 전일 연가/병가/특별휴가: -{calc.LeaveDays}일");
        sb.AppendLine($"- 조퇴·외출·지각: {calc.PartialHours}시간 (환산 차감: -{calc.PartialConvertedDays}일, 잔여: {calc.PartialRemainingHours}시간)");
        sb.AppendLine($"- 최종 인정 출근일수: {calc.NetWorkdays}일 / 15일");
        sb.AppendLine($"- 15일 수당 판정: {(calc.IsEligible15Days ? "✅ 15일 충족 (수당 100% 전액 지급)" : $"❌ 15일 미달 ({Math.Abs(calc.DaysDifferenceFrom15)}일 부족, 일할 감액)")}");
        if (calc.IsEligible15Days)
        {
            sb.AppendLine($"- 수당 감액 없는 추가 사용 가능 연가: 최대 {calc.UsableLeaveWithoutDeduction}일");
        }

        try
        {
            Clipboard.SetText(sb.ToString());
            MessageBox.Show("복무 및 출근일수 정산 보고서가 클립보드에 복사되었습니다!", "복사 완료", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"복사 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
