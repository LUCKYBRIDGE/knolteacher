using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;
using Microsoft.Win32;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class QrCodeModalDialog : Window
{
    private readonly IQrCodeService _qrCodeService;
    private string _currentUrl = string.Empty;

    public QrCodeModalDialog(IQrCodeService qrCodeService, string title = "📱 QR 코드", string url = "https://knolteacher.com")
    {
        _qrCodeService = qrCodeService;
        InitializeComponent();

        TxtTitle.Text = title;
        _currentUrl = url;
        TbUrl.Text = url;
        RenderQr();
    }

    private void RenderQr()
    {
        try
        {
            ImgQrCode.Source = _qrCodeService.GenerateQrBitmap(_currentUrl, 12);
        }
        catch { }
    }

    private void TbUrl_TextChanged(object sender, TextChangedEventArgs e)
    {
        _currentUrl = TbUrl.Text.Trim();
        RenderQr();
    }

    private void BtnCopyUrl_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            Clipboard.SetText(_currentUrl);
            HudNotificationWindow.Instance.ShowToast("📋", "URL 주소가 클립보드에 복사되었습니다.");
        }
        catch { }
    }

    private void BtnCopyImage_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            _qrCodeService.CopyQrToClipboard(_currentUrl);
            HudNotificationWindow.Instance.ShowToast("📱", "QR 코드 이미지가 클립보드에 복사되었습니다.");
        }
        catch { }
    }

    private void BtnSaveImage_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var sfd = new SaveFileDialog
            {
                Filter = "PNG 이미지 (*.png)|*.png",
                FileName = $"QR_{DateTime.Now:yyyyMMdd_HHmmss}.png"
            };

            if (sfd.ShowDialog() == true)
            {
                _qrCodeService.SaveQrToFile(_currentUrl, sfd.FileName);
                HudNotificationWindow.Instance.ShowToast("💾", "QR 코드 이미지가 저장되었습니다.");
            }
        }
        catch { }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
