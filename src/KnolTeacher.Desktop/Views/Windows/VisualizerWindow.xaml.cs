using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using DirectShowLib;
using OpenCvSharp;
using OpenCvSharp.WpfExtensions;

using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class VisualizerWindow : System.Windows.Window
{
    private readonly IDisplayManager? _displayManager;
    private int _currentMonitorIndex = 1;

    private VideoCapture? _capture;
    private CancellationTokenSource? _cts;

    private int _rotationAngle = 0; // 0, 90, 180, 270
    private bool _flipH = false;
    private bool _flipV = false;
    private bool _isFrozen = false;
    private bool _isDocEnhance = false;
    private Mat? _frozenFrame;

    public VisualizerWindow(IDisplayManager? displayManager = null)
    {
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        InitializeComponent();
        Loaded += (s, e) =>
        {
            RefreshCameras();
            PositionToDefaultMonitor();
        };
    }

    public void PositionToDefaultMonitor()
    {
        if (_displayManager != null)
        {
            _currentMonitorIndex = _displayManager.RecommendedStudentMonitorIndex;
            _displayManager.MoveToStudentMonitor(this, maximize: false);
            UpdateMonitorButtonText();
        }
    }

    private void UpdateMonitorButtonText()
    {
        if (BtnSwitchMonitor != null)
        {
            BtnSwitchMonitor.Content = _currentMonitorIndex == 1 ? "📺 모니터 2 (학생용)" : "💻 모니터 1 (메인)";
        }
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        if (_displayManager == null || _displayManager.ScreenCount < 2) return;
        _currentMonitorIndex = _currentMonitorIndex == 1 ? 0 : 1;
        _displayManager.MoveWindowToScreen(this, _currentMonitorIndex, maximize: false);
        UpdateMonitorButtonText();
    }

    private void RefreshCameras()
    {
        CbCameras.Items.Clear();
        var devices = DsDevice.GetDevicesOfCat(FilterCategory.VideoInputDevice);

        if (devices.Length == 0)
        {
            CbCameras.Items.Add("카메라 없음");
            CbCameras.SelectedIndex = 0;
            TxtStatus.Text = "연결된 카메라가 없습니다";
            return;
        }

        foreach (var dev in devices)
        {
            CbCameras.Items.Add(dev.Name);
        }

        CbCameras.SelectedIndex = 0;
    }

    private void CbCameras_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CbCameras.SelectedIndex >= 0 && CbCameras.SelectedItem is string name && name != "카메라 없음")
        {
            StartCamera(CbCameras.SelectedIndex);
        }
    }

    private void BtnRefresh_Click(object sender, RoutedEventArgs e)
    {
        RefreshCameras();
    }

    private void StartCamera(int deviceIndex)
    {
        StopCamera();

        _cts = new CancellationTokenSource();
        var token = _cts.Token;

        Task.Run(() =>
        {
            try
            {
                Dispatcher.Invoke(() => TxtStatus.Text = "카메라 연결 중...");

                // Open with DirectShow for BestCam / USB Visualizers
                _capture = new VideoCapture(deviceIndex, VideoCaptureAPIs.DSHOW);

                // Safe Default: 640x480 for BestCam S3 compatibility
                _capture.Set(VideoCaptureProperties.FrameWidth, 640);
                _capture.Set(VideoCaptureProperties.FrameHeight, 480);

                if (!_capture.IsOpened())
                {
                    Dispatcher.Invoke(() => TxtStatus.Text = "카메라 열기 실패");
                    return;
                }

                Dispatcher.Invoke(() => TxtStatus.Text = "실시간 스트리밍 중");

                using var rawFrame = new Mat();
                int blackFrameCount = 0;

                while (!token.IsCancellationRequested && _capture.IsOpened())
                {
                    if (_isFrozen && _frozenFrame != null)
                    {
                        RenderFrame(_frozenFrame);
                        Thread.Sleep(33);
                        continue;
                    }

                    if (!_capture.Read(rawFrame) || rawFrame.Empty())
                    {
                        Thread.Sleep(10);
                        continue;
                    }

                    // Auto-Healing: Check for black frame issue
                    var mean = Cv2.Mean(rawFrame).Val0;
                    if (mean < 0.5)
                    {
                        blackFrameCount++;
                        if (blackFrameCount > 15) // ~0.5 sec black screen
                        {
                            // Reset to safe 640x480
                            _capture.Set(VideoCaptureProperties.FrameWidth, 640);
                            _capture.Set(VideoCaptureProperties.FrameHeight, 480);
                            blackFrameCount = 0;
                        }
                    }
                    else
                    {
                        blackFrameCount = 0;
                    }

                    using var processed = rawFrame.Clone();

                    // 1. Rotation
                    if (_rotationAngle == 90) Cv2.Rotate(processed, processed, RotateFlags.Rotate90Clockwise);
                    else if (_rotationAngle == 180) Cv2.Rotate(processed, processed, RotateFlags.Rotate180);
                    else if (_rotationAngle == 270) Cv2.Rotate(processed, processed, RotateFlags.Rotate90Counterclockwise);

                    // 2. Flip
                    if (_flipH && _flipV) Cv2.Flip(processed, processed, FlipMode.XY);
                    else if (_flipH) Cv2.Flip(processed, processed, FlipMode.Y);
                    else if (_flipV) Cv2.Flip(processed, processed, FlipMode.X);

                    // 3. Document Enhancement Filter
                    if (_isDocEnhance)
                    {
                        using var gray = new Mat();
                        Cv2.CvtColor(processed, gray, ColorConversionCodes.BGR2GRAY);
                        Cv2.AdaptiveThreshold(gray, gray, 255, AdaptiveThresholdTypes.GaussianC, ThresholdTypes.Binary, 15, 8);
                        Cv2.CvtColor(gray, processed, ColorConversionCodes.GRAY2BGR);
                    }

                    RenderFrame(processed);
                    Thread.Sleep(16); // Target ~60 FPS
                }
            }
            catch (Exception ex)
            {
                Dispatcher.Invoke(() => TxtStatus.Text = $"오류: {ex.Message}");
            }
        }, token);
    }

    private void RenderFrame(Mat frame)
    {
        Dispatcher.Invoke(() =>
        {
            try
            {
                var bmp = frame.ToWriteableBitmap();
                CameraImage.Source = bmp;
            }
            catch
            {
                // ignore transient frame error
            }
        });
    }

    private void StopCamera()
    {
        _cts?.Cancel();
        _capture?.Dispose();
        _capture = null;
    }

    private void BtnRotate_Click(object sender, RoutedEventArgs e)
    {
        _rotationAngle = (_rotationAngle + 90) % 360;
    }

    private void BtnFlipH_Click(object sender, RoutedEventArgs e)
    {
        _flipH = !_flipH;
    }

    private void BtnFlipV_Click(object sender, RoutedEventArgs e)
    {
        _flipV = !_flipV;
    }

    private void BtnFreeze_Checked(object sender, RoutedEventArgs e)
    {
        _isFrozen = true;
    }

    private void BtnFreeze_Unchecked(object sender, RoutedEventArgs e)
    {
        _isFrozen = false;
        _frozenFrame?.Dispose();
        _frozenFrame = null;
    }

    private void BtnDocEnhance_Checked(object sender, RoutedEventArgs e)
    {
        _isDocEnhance = true;
    }

    private void BtnDocEnhance_Unchecked(object sender, RoutedEventArgs e)
    {
        _isDocEnhance = false;
    }

    private void BtnSnapshot_Click(object sender, RoutedEventArgs e)
    {
        if (CameraImage.Source is BitmapSource bmp)
        {
            try
            {
                var picturesDir = Environment.GetFolderPath(Environment.SpecialFolder.MyPictures);
                var saveDir = System.IO.Path.Combine(picturesDir, "KnolTeacher_Visualizer");
                Directory.CreateDirectory(saveDir);

                var fileName = $"스냅샷_{DateTime.Now:yyyyMMdd_HHmmss}.png";
                var fullPath = System.IO.Path.Combine(saveDir, fileName);

                var encoder = new PngBitmapEncoder();
                encoder.Frames.Add(BitmapFrame.Create(bmp));
                using (var fs = new FileStream(fullPath, FileMode.Create))
                {
                    encoder.Save(fs);
                }

                MessageBox.Show($"스냅샷이 저장되었습니다:\n{fullPath}", "캡처 완료", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"스냅샷 저장 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Hide();
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        StopCamera();
        Hide();
    }
}
