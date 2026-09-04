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

        Loaded += (s, e) => RenderQr();
    }

    private void RenderQr()
    {
        try
        {
            string text = TbWidgetUrl.Text.Trim();
            if (string.IsNullOrEmpty(text)) text = "https://pinky-ne.com/";
            ImgWidgetQr.Source = _qrCodeService.GenerateQrBitmap(text, 8);
        }
        catch { }
    }

    private void TbWidgetUrl_TextChanged(object sender, TextChangedEventArgs e) => RenderQr();

    private void BtnCopy_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            string text = TbWidgetUrl.Text.Trim();
            _qrCodeService.CopyQrToClipboard(text);
            HudNotificationWindow.Instance.ShowToast("📱", "QR 코드 이미지가 복사되었습니다.");
        }
        catch { }
    }

    private void BtnZoom_Click(object sender, RoutedEventArgs e)
    {
        string text = TbWidgetUrl.Text.Trim();
        var dlg = new QrCodeModalDialog(_qrCodeService, "📱 실시간 수업 QR 코드", text)
        {
            Owner = Window.GetWindow(this)
        };
        dlg.ShowDialog();
    }
}
