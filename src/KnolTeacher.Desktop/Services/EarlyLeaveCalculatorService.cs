using System;
using System.Collections.Generic;
using System.Linq;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public class EarlyLeaveCalculatorService : IEarlyLeaveCalculatorService
{
    private static readonly string[] DayOffKeywords = new[]
    {
        "공휴일", "대체공휴일", "대체휴일", "임시공휴일", "재량휴업", "재량휴업일", "학교장재량휴업일",
        "휴업일", "휴교", "개교기념일", "여름방학", "겨울방학", "봄방학", "학년말방학", "방학",
        "신정", "설날", "삼일절", "어린이날", "부처님오신날", "현충일", "광복절", "추석", "개천절",
        "한글날", "크리스마스", "기독탄신일", "근로자의날", "선거일"
    };

    public EarlyLeaveCalculationResult Calculate(int year, int month, List<AcademicScheduleItem>? schedules = null, int requiredDays = 15)
    {
        var result = new EarlyLeaveCalculationResult
        {
            Year = year,
            Month = month,
            RequiredWorkDays = requiredDays
        };

        int daysInMonth = DateTime.DaysInMonth(year, month);
        result.TotalCalendarDays = daysInMonth;

        var offDays = new HashSet<DateTime>();

        // 1. Weekend days
        int weekendCount = 0;
        for (int day = 1; day <= daysInMonth; day++)
        {
            var date = new DateTime(year, month, day);
            if (date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday)
            {
                weekendCount++;
                offDays.Add(date);
            }
        }
        result.WeekendDays = weekendCount;

        // 2. Schedule holidays/vacations on weekdays
        int holidayCount = 0;
        if (schedules != null)
        {
            foreach (var item in schedules)
            {
                if (item.Date.HasValue)
                {
                    var dt = item.Date.Value;
                    if (dt.Year == year && dt.Month == month && dt.DayOfWeek != DayOfWeek.Saturday && dt.DayOfWeek != DayOfWeek.Sunday)
                    {
                        bool isOff = item.IsHoliday || DayOffKeywords.Any(kw => (item.EventName ?? "").Contains(kw, StringComparison.OrdinalIgnoreCase));
                        if (isOff && !offDays.Contains(dt))
                        {
                            holidayCount++;
                            offDays.Add(dt);
                        }
                    }
                }
            }
        }
        result.HolidayAndVacationDays = holidayCount;

        int netWorkDays = daysInMonth - weekendCount - holidayCount;
        result.NetWorkDays = Math.Max(0, netWorkDays);
        result.OffDays = offDays.OrderBy(d => d).ToList();

        if (result.IsEligibleForEarlyLeave)
        {
            result.SummaryMessage = $"이번 달 실근무일수는 총 {result.NetWorkDays}일로, 기준({requiredDays}일)보다 {result.MarginDays}일 여유가 있어 조퇴/연가 사용이 가능합니다.";
        }
        else
        {
            int shortDays = requiredDays - result.NetWorkDays;
            result.SummaryMessage = $"이번 달 실근무일수는 총 {result.NetWorkDays}일로, 기준({requiredDays}일)보다 {shortDays}일 부족하여 조퇴/외출 시 복무 요건 확인이 필요합니다.";
        }

        return result;
    }
}
