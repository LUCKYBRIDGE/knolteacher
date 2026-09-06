using System;
using System.Collections.Generic;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IEarlyLeaveCalculatorService
{
    EarlyLeaveCalculationResult Calculate(int year, int month, List<AcademicScheduleItem>? schedules = null, int requiredDays = 15);
}
