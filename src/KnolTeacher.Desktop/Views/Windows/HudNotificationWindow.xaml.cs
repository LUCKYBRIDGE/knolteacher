using System;
using System.Windows;
using System.Windows.Media.Animation;
using System.Windows.Threading;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class HudNotificationWindow : Window
{
    private static HudNotificationWindow? _instance;
    private readonly DispatcherTimer _hideTimer;

    public static HudNotificationWindow Instance => _instance ??= new HudNotificationWindow();

    public HudNotificationWindow()
    {
        InitializeComponent();
        _instance = this;

        _hideTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(1300)
        };
        _hideTimer.Tick += (s, e) =>
        {
            _hideTimer.Stop();
            FadeOut();
        };
    }

    public void ShowToast(string icon, string message)
    {
        Dispatcher.Invoke(() =>
        {
            TxtIcon.Text = icon;
            TxtMessage.Text = message;

            UpdateLayout();
            double screenWidth = SystemParameters.PrimaryScreenWidth;
            double w = ActualWidth > 0 ? ActualWidth : 220;
            Left = (screenWidth - w) / 2;
            Top = 20;

            if (!IsVisible)
            {
                Show();
            }

            _hideTimer.Stop();

            var fadeIn = new DoubleAnimation(0, 1.0, TimeSpan.FromMilliseconds(150));
            HudBorder.BeginAnimation(UIElement.OpacityProperty, fadeIn);

            _hideTimer.Start();
        });
    }

    private void FadeOut()
    {
        var fadeOut = new DoubleAnimation(1.0, 0, TimeSpan.FromMilliseconds(250));
        fadeOut.Completed += (s, e) =>
        {
            if (HudBorder.Opacity == 0)
            {
                Hide();
            }
        };
        HudBorder.BeginAnimation(UIElement.OpacityProperty, fadeOut);
    }
}
