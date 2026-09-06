using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class AppUpdateDialog : Window
{
    private readonly IUpdateService _updateService;
    private readonly UpdateInfo _updateInfo;
    private CancellationTokenSource? _cts;
    private bool _isUpdating = false;

    public AppUpdateDialog(IUpdateService updateService, UpdateInfo updateInfo)
    {
        InitializeComponent();
        _updateService = updateService;
        _updateInfo = updateInfo;

        TxtCurrentVersion.Text = $"현재 버전: {_updateInfo.CurrentVersion}";
        TxtLatestVersion.Text = $"최신 버전: {_updateInfo.LatestVersion}";
        TxtReleaseTitle.Text = string.IsNullOrWhiteSpace(_updateInfo.ReleaseTitle) ? $"{_updateInfo.LatestVersion} 업데이트 안내" : _updateInfo.ReleaseTitle;
        TxtReleaseNotes.Text = string.IsNullOrWhiteSpace(_updateInfo.ReleaseNotes) ? "새로운 기능과 성능 개선 및 버그 수정이 포함되어 있습니다." : _updateInfo.ReleaseNotes;

        if (_updateInfo.AssetSize > 0)
        {
            double mb = _updateInfo.AssetSize / (1024.0 * 1024.0);
            TxtStatus.Text = $"다운로드 크기: {mb:0.0} MB • 원클릭 자동 업데이트";
        }
    }

    private async void BtnStartUpdate_Click(object sender, RoutedEventArgs e)
    {
        if (_isUpdating) return;
        _isUpdating = true;

        BtnStartUpdate.IsEnabled = false;
        BtnLater.Content = "취소";
        ProgressBarUpdate.Visibility = Visibility.Visible;
        TxtProgressPercent.Visibility = Visibility.Visible;
        TxtDownloadDetails.Visibility = Visibility.Visible;
        TxtStatus.Text = "최신 패키지를 다운로드하는 중입니다...";

        _cts = new CancellationTokenSource();

        var progress = new Progress<(long downloaded, long total, double percentage)>(p =>
        {
            ProgressBarUpdate.Value = p.percentage;
            TxtProgressPercent.Text = $"{p.percentage:0}%";
            double downMb = p.downloaded / (1024.0 * 1024.0);
            double totalMb = p.total / (1024.0 * 1024.0);
            TxtDownloadDetails.Text = $"{downMb:0.0} MB / {totalMb:0.0} MB";
        });

        try
        {
            string downloadedPath = await _updateService.DownloadUpdateAsync(_updateInfo, progress, _cts.Token);
            TxtStatus.Text = "다운로드 완료! 프로그램을 재시작하여 업데이트를 적용합니다.";
            await Task.Delay(1000);
            _updateService.ApplyUpdateAndRestart(downloadedPath);
        }
        catch (OperationCanceledException)
        {
            TxtStatus.Text = "업데이트 다운로드가 취소되었습니다.";
            ResetUi();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"업데이트 다운로드 중 오류가 발생했습니다:\n{ex.Message}", "업데이트 실패", MessageBoxButton.OK, MessageBoxImage.Error);
            ResetUi();
        }
    }

    private void ResetUi()
    {
        _isUpdating = false;
        BtnStartUpdate.IsEnabled = true;
        BtnLater.Content = "나중에 하기";
        ProgressBarUpdate.Visibility = Visibility.Collapsed;
        TxtProgressPercent.Visibility = Visibility.Collapsed;
        TxtDownloadDetails.Visibility = Visibility.Collapsed;
    }

    private void BtnLater_Click(object sender, RoutedEventArgs e)
    {
        if (_isUpdating)
        {
            _cts?.Cancel();
        }
        else
        {
            Close();
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        if (_isUpdating)
        {
            _cts?.Cancel();
        }
        Close();
    }
}
