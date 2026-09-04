using System;
using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using QRCoder;

namespace KnolTeacher.Desktop.Services;

public interface IQrCodeService
{
    BitmapSource GenerateQrBitmap(string content, int pixelsPerModule = 10);
    byte[] GenerateQrPngBytes(string content, int pixelsPerModule = 10);
    void CopyQrToClipboard(string content);
    void SaveQrToFile(string content, string filePath);
}

public class QrCodeService : IQrCodeService
{
    public BitmapSource GenerateQrBitmap(string content, int pixelsPerModule = 10)
    {
        if (string.IsNullOrWhiteSpace(content)) content = "https://knolteacher.com";

        using var qrGenerator = new QRCodeGenerator();
        using var qrCodeData = qrGenerator.CreateQrCode(content, QRCodeGenerator.ECCLevel.Q);
        using var qrCode = new PngByteQRCode(qrCodeData);
        byte[] qrCodeBytes = qrCode.GetGraphic(pixelsPerModule);

        var image = new BitmapImage();
        using var mem = new MemoryStream(qrCodeBytes);
        image.BeginInit();
        image.CacheOption = BitmapCacheOption.OnLoad;
        image.StreamSource = mem;
        image.EndInit();
        image.Freeze();
        return image;
    }

    public byte[] GenerateQrPngBytes(string content, int pixelsPerModule = 10)
    {
        if (string.IsNullOrWhiteSpace(content)) content = "https://knolteacher.com";

        using var qrGenerator = new QRCodeGenerator();
        using var qrCodeData = qrGenerator.CreateQrCode(content, QRCodeGenerator.ECCLevel.Q);
        using var qrCode = new PngByteQRCode(qrCodeData);
        return qrCode.GetGraphic(pixelsPerModule);
    }

    public void CopyQrToClipboard(string content)
    {
        try
        {
            var bitmap = GenerateQrBitmap(content, 12);
            Clipboard.SetImage(bitmap);
        }
        catch { }
    }

    public void SaveQrToFile(string content, string filePath)
    {
        try
        {
            byte[] bytes = GenerateQrPngBytes(content, 16);
            File.WriteAllBytes(filePath, bytes);
        }
        catch { }
    }
}
