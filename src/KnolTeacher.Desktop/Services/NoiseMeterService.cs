using System;
using System.Collections.Generic;
using NAudio.Wave;

namespace KnolTeacher.Desktop.Services;

public enum NoiseState
{
    Green,  // 조용함
    Yellow, // 주의
    Red     // 경고
}

public interface INoiseMeterService
{
    bool IsRunning { get; }
    double CurrentDecibel { get; }
    NoiseState CurrentState { get; }
    int WarningCount { get; }
    double YellowThreshold { get; set; }
    double RedThreshold { get; set; }
    bool PlayAlarmOnRed { get; set; }

    event Action<double, NoiseState, int>? NoiseUpdated;
    event Action? RedWarningTriggered;

    void Start(int deviceIndex = 0);
    void Stop();
    void ResetWarningCount();
    List<string> GetInputDevices();
}

public class NoiseMeterService : INoiseMeterService, IDisposable
{
    private WaveInEvent? _waveIn;
    private double _smoothedDb = 35.0;
    private DateTime _redStartTime = DateTime.MinValue;
    private bool _inRedSustained = false;

    public bool IsRunning => _waveIn != null;
    public double CurrentDecibel => _smoothedDb;
    public NoiseState CurrentState { get; private set; } = NoiseState.Green;
    public int WarningCount { get; private set; } = 0;

    public double YellowThreshold { get; set; } = 55.0; // dB
    public double RedThreshold { get; set; } = 75.0;    // dB
    public bool PlayAlarmOnRed { get; set; } = true;

    public event Action<double, NoiseState, int>? NoiseUpdated;
    public event Action? RedWarningTriggered;

    public List<string> GetInputDevices()
    {
        var list = new List<string>();
        int waveInDevices = WaveIn.DeviceCount;
        for (int n = 0; n < waveInDevices; n++)
        {
            var caps = WaveIn.GetCapabilities(n);
            list.Add(caps.ProductName);
        }
        return list;
    }

    public void Start(int deviceIndex = 0)
    {
        if (IsRunning) Stop();

        try
        {
            if (WaveIn.DeviceCount == 0) return;

            int actualIndex = Math.Min(Math.Max(0, deviceIndex), WaveIn.DeviceCount - 1);
            _waveIn = new WaveInEvent
            {
                DeviceNumber = actualIndex,
                WaveFormat = new WaveFormat(16000, 16, 1),
                BufferMilliseconds = 50
            };

            _waveIn.DataAvailable += OnDataAvailable;
            _waveIn.StartRecording();
        }
        catch (Exception ex)
        {
            App.BootLog($"[NoiseMeterService.Start] Error: {ex.Message}");
            Stop();
        }
    }

    public void Stop()
    {
        if (_waveIn != null)
        {
            try
            {
                _waveIn.DataAvailable -= OnDataAvailable;
                _waveIn.StopRecording();
                _waveIn.Dispose();
            }
            catch { }
            finally
            {
                _waveIn = null;
            }
        }
        _inRedSustained = false;
    }

    public void ResetWarningCount()
    {
        WarningCount = 0;
        NoiseUpdated?.Invoke(_smoothedDb, CurrentState, WarningCount);
    }

    private void OnDataAvailable(object? sender, WaveInEventArgs e)
    {
        if (e.BytesRecorded == 0) return;

        double sum = 0;
        int sampleCount = e.BytesRecorded / 2;

        for (int index = 0; index < e.BytesRecorded; index += 2)
        {
            short sample = (short)((e.Buffer[index + 1] << 8) | e.Buffer[index]);
            sum += sample * sample;
        }

        double rms = Math.Sqrt(sum / sampleCount);

        // Map RMS (0 ~ 32767) to approximate decibels (30 dB ~ 100 dB)
        double rawDb = 30.0;
        if (rms > 1.0)
        {
            rawDb = 20.0 * Math.Log10(rms);
            // Scale and shift so ambient quiet room is ~35-42 dB, loud speaking is ~70-85 dB
            rawDb = Math.Max(30.0, Math.Min(100.0, 30.0 + (rawDb * 0.8)));
        }

        // Smooth with EMA filter (alpha = 0.25 for responsive yet calm display)
        _smoothedDb = (_smoothedDb * 0.75) + (rawDb * 0.25);

        // Determine State
        NoiseState newState;
        if (_smoothedDb >= RedThreshold)
        {
            newState = NoiseState.Red;
            if (_redStartTime == DateTime.MinValue)
            {
                _redStartTime = DateTime.Now;
            }
            else if ((DateTime.Now - _redStartTime).TotalSeconds >= 1.2 && !_inRedSustained)
            {
                _inRedSustained = true;
                WarningCount++;
                RedWarningTriggered?.Invoke();
            }
        }
        else if (_smoothedDb >= YellowThreshold)
        {
            newState = NoiseState.Yellow;
            _redStartTime = DateTime.MinValue;
            _inRedSustained = false;
        }
        else
        {
            newState = NoiseState.Green;
            _redStartTime = DateTime.MinValue;
            _inRedSustained = false;
        }

        CurrentState = newState;
        NoiseUpdated?.Invoke(_smoothedDb, CurrentState, WarningCount);
    }

    public void Dispose()
    {
        Stop();
    }
}
