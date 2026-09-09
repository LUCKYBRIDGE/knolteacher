using System;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class QrWidgetView : UserControl
{
    private readonly IQrCodeService _qrCodeService;

    public QrWidgetView(IQrCodeService? qrCodeService = null)
    {
        _qrCodeService = qrCodeService ?? new QrCodeService();
        InitializeComponent();
        Loaded += (_, _) => RenderQr();
    }

    private string CurrentText
    {
        get
        {
            string text = TbWidgetUrl.Text.Trim();
            return string.IsNullOrWhiteSpace(text) ? "https://pinky-ne.com/" : text;
        }
    }

    private void RenderQr()
    {
        try
        {
            ImgWidgetQr.Source = _qrCodeService.GenerateQrBitmap(CurrentText, 8);
            ImgWidgetQr.ToolTip = null;
        }
        catch (Exception ex)
        {
            ImgWidgetQr.Source = null;
            ImgWidgetQr.ToolTip = $"QR 코드를 만들 수 없습니다. ({ex.GetType().Name})";
            System.Diagnostics.Debug.WriteLine($"[Nolboard.QR] Render failed: {ex.GetType().Name}");
        }
    }

    private void TbWidgetUrl_TextChanged(object sender, TextChangedEventArgs e) => RenderQr();

    private void BtnCopy_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            _qrCodeService.CopyQrToClipboard(CurrentText);
            HudNotificationWindow.Instance.ShowToast("📱", "QR 코드 이미지가 복사되었습니다.");
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Nolboard.QR] Copy failed: {ex.GetType().Name}");
            HudNotificationWindow.Instance.ShowToast("⚠️", "QR 코드를 복사하지 못했습니다. 잠시 후 다시 시도해 주세요.");
        }
    }

    private void BtnZoom_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dialog = new QrCodeModalDialog(_qrCodeService, "📱 실시간 수업 QR 코드", CurrentText)
            {
                Owner = Window.GetWindow(this)
            };
            dialog.ShowDialog();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[Nolboard.QR] Zoom failed: {ex.GetType().Name}");
            HudNotificationWindow.Instance.ShowToast("⚠️", "QR 코드를 크게 표시하지 못했습니다.");
        }
    }
}
