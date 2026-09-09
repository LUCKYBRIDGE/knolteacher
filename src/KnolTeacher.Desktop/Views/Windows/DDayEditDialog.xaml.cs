using System;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class DDayEditDialog : Window
{
    private readonly IConfigService _configService;
    public DDayConfig ResultConfig { get; private set; }

    public static event Action<DDayConfig>? OnDDayChanged;

    public static void NotifyDDayChanged(DDayConfig config)
    {
        OnDDayChanged?.Invoke(config);
    }

    public DDayEditDialog(IConfigService configService)
    {
        _configService = configService;
        ResultConfig = new DDayConfig
        {
            Title = _configService.DDayConfig.Title,
            TargetDate = _configService.DDayConfig.TargetDate,
            IsActive = _configService.DDayConfig.IsActive
        };

        InitializeComponent();

        TbTitle.Text = ResultConfig.Title;
        DpTargetDate.SelectedDate = ResultConfig.TargetDate;
        UpdatePreview();
    }

    private void BtnPreset_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            TbTitle.Text = tag;
            UpdatePreview();
        }
    }

    private void TbTitle_TextChanged(object sender, TextChangedEventArgs e)
    {
        UpdatePreview();
    }

    private void DpTargetDate_SelectedDateChanged(object sender, SelectionChangedEventArgs e)
    {
        UpdatePreview();
    }

    private void UpdatePreview()
    {
        if (TxtPreviewTitle == null || TxtPreviewDate == null || TxtPreviewDDay == null) return;

        string title = string.IsNullOrWhiteSpace(TbTitle?.Text) ? "목표일" : TbTitle.Text.Trim();
        DateTime target = DpTargetDate?.SelectedDate ?? DateTime.Today;

        TxtPreviewTitle.Text = title;
        TxtPreviewDate.Text = target.ToString("yyyy-MM-dd (ddd)");

        int days = (target.Date - DateTime.Today).Days;
        TxtPreviewDDay.Text = days == 0 ? "D-Day!" : (days > 0 ? $"D-{days}" : $"D+{-days}");
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        string title = string.IsNullOrWhiteSpace(TbTitle.Text) ? "목표일" : TbTitle.Text.Trim();
        DateTime target = DpTargetDate.SelectedDate ?? DateTime.Today;

        ResultConfig.Title = title;
        ResultConfig.TargetDate = target;
        ResultConfig.IsActive = true;

        _configService.DDayConfig = ResultConfig;
        _configService.SaveDDayConfig();

        NotifyDDayChanged(ResultConfig);

        DialogResult = true;
        Close();
    }
}
