using System;
using System.Diagnostics;
using System.Speech.Synthesis;
using System.Threading;
using System.Threading.Tasks;

namespace KnolTeacher.Desktop.Services;

public class TtsService : ITtsService, IDisposable
{
    private SpeechSynthesizer? _synth;
    private bool _isSpeaking = false;
    private readonly object _lock = new();

    public bool IsSpeaking
    {
        get => _isSpeaking;
        private set
        {
            if (_isSpeaking != value)
            {
                _isSpeaking = value;
                SpeakingStateChanged?.Invoke(_isSpeaking);
            }
        }
    }

    public event Action<bool>? SpeakingStateChanged;

    public TtsService()
    {
        try
        {
            _synth = new SpeechSynthesizer();
            // Try to find Korean voice if available
            foreach (var voice in _synth.GetInstalledVoices())
            {
                if (voice.Enabled && voice.VoiceInfo.Culture.Name.StartsWith("ko", StringComparison.OrdinalIgnoreCase))
                {
                    _synth.SelectVoice(voice.VoiceInfo.Name);
                    break;
                }
            }

            _synth.SpeakCompleted += (s, e) =>
            {
                lock (_lock)
                {
                    IsSpeaking = false;
                }
            };
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[TtsService] Init error: {ex.Message}");
        }
    }

    public Task SpeakAsync(string text, int rate = 0, int volume = 100)
    {
        if (string.IsNullOrWhiteSpace(text) || _synth == null) return Task.CompletedTask;

        return Task.Run(() =>
        {
            lock (_lock)
            {
                Stop();
                try
                {
                    _synth.Rate = Math.Max(-10, Math.Min(10, rate));
                    _synth.Volume = Math.Max(0, Math.Min(100, volume));
                    IsSpeaking = true;
                    _synth.SpeakAsync(text.Trim());
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"[TtsService] SpeakAsync error: {ex.Message}");
                    IsSpeaking = false;
                }
            }
        });
    }

    public void Stop()
    {
        lock (_lock)
        {
            try
            {
                if (_synth != null && _synth.State == SynthesizerState.Speaking)
                {
                    _synth.SpeakAsyncCancelAll();
                }
            }
            catch { }
            IsSpeaking = false;
        }
    }

    public void Dispose()
    {
        Stop();
        _synth?.Dispose();
        _synth = null;
    }
}
