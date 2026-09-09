using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class DDayWidgetView : UserControl
{
    private readonly IConfigService _configService;

    public DDayWidgetView(IConfigService? configService = null)
    {
        _configService = configService ?? ((Application.Current as App)?.Services?.GetService(typeof(IConfigService)) as IConfigService)!;
        InitializeComponent();

        Loaded += (s, e) => UpdateDisplay(_configService.DDayConfig);

        DDayEditDialog.OnDDayChanged += (cfg) =>
        {
            Dispatcher.Invoke(() => UpdateDisplay(cfg));
        };
    }

    private void UpdateDisplay(DDayConfig cfg)
    {
        if (cfg == null) return;

        TxtDDayTitle.Text = string.IsNullOrWhiteSpace(cfg.Title) ? "목표일" : cfg.Title;
        TxtDDayTarget.Text = $"목표일: {cfg.TargetDate:yyyy-MM-dd (ddd)}";

        int days = (cfg.TargetDate.Date - DateTime.Today).Days;
        if (days == 0)
        {
            TxtDDayCount.Text = "D-Day!";
            TxtDDayCount.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));
            TxtBadgeStatus.Text = "오늘 당일!";
            TxtDDaySub.Text = "🎉 드디어 목표일 당일입니다! 모두 축하합니다!";
        }
        else if (days > 0)
        {
            TxtDDayCount.Text = $"D-{days}";
            TxtDDayCount.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F59E0B"));
            TxtBadgeStatus.Text = $"{days}일 남음";
            TxtDDaySub.Text = $"목표일까지 앞으로 {days}일 남았습니다.";
        }
        else
        {
            TxtDDayCount.Text = $"D+{-days}";
            TxtDDayCount.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8"));
            TxtBadgeStatus.Text = "목표일 경과";
            TxtDDaySub.Text = $"목표일로부터 {-days}일 지났습니다.";
        }
    }

    private void BtnChangeDDay_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new DDayEditDialog(_configService)
        {
            Owner = Window.GetWindow(this)
        };
        dlg.ShowDialog();
    }
}
