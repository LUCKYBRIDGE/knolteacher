using System;
using System.Collections.Generic;
using System.Linq;

namespace KnolTeacher.Desktop.Services;

public class WorkdayMonthCalculation
{
    public int Year { get; set; }
    public int Month { get; set; }
    public int TotalWeekdays { get; set; }
    public int Holidays { get; set; }
    public int VacationDays { get; set; }
    public int LeaveDays { get; set; } // 연가/병가 등
    public int PartialHours { get; set; } // 조퇴/외출/지각 누적 시간 (8시간 = 1일)
    public int PartialConvertedDays => PartialHours / 8;
    public int PartialRemainingHours => PartialHours % 8;

    public int NetWorkdays => Math.Max(0, TotalWeekdays - Holidays - VacationDays - LeaveDays - PartialConvertedDays);
    public bool IsEligible15Days => NetWorkdays >= 15;
    public int DaysDifferenceFrom15 => NetWorkdays - 15; // Positive = margin, Negative = short
    public int UsableLeaveWithoutDeduction => Math.Max(0, NetWorkdays - 15);
}

public interface IWorkdayCalculatorService
{
    WorkdayMonthCalculation Calculate(int year, int month, int holidays, int vacationDays, int leaveDays, int partialHours);
    int GetStandardHolidays(int year, int month);
}

public class WorkdayCalculatorService : IWorkdayCalculatorService
{
    public WorkdayMonthCalculation Calculate(int year, int month, int holidays, int vacationDays, int leaveDays, int partialHours)
    {
        int daysInMonth = DateTime.DaysInMonth(year, month);
        int weekdays = 0;

        for (int d = 1; d <= daysInMonth; d++)
        {
            var dt = new DateTime(year, month, d);
            if (dt.DayOfWeek != DayOfWeek.Saturday && dt.DayOfWeek != DayOfWeek.Sunday)
            {
                weekdays++;
            }
        }

        var calc = new WorkdayMonthCalculation
        {
            Year = year,
            Month = month,
            TotalWeekdays = weekdays,
            Holidays = holidays,
            VacationDays = vacationDays,
            LeaveDays = leaveDays,
            PartialHours = partialHours
        };

        return calc;
    }

    public int GetStandardHolidays(int year, int month)
    {
        // Korean legal holidays (approximate standard weekdays count)
        int h = 0;
        switch (month)
        {
            case 1: // 신정, 설날
                h = 2; break;
            case 2: // 설날 대체휴일
                h = 1; break;
            case 3: // 삼일절
                h = 1; break;
            case 5: // 어린이날, 부처님오신날
                h = 2; break;
            case 6: // 현충일
                h = 1; break;
            case 8: // 광복절
                h = 1; break;
            case 9:
            case 10: // 추석, 개천절, 한글날
                h = 2; break;
            case 12: // 성탄절
                h = 1; break;
            default:
                h = 0; break;
        }
        return h;
    }
}
