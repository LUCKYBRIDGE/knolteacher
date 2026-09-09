using System;
using System.IO;
using System.Media;
using System.Threading.Tasks;

namespace KnolTeacher.Desktop.Services;

public interface ISoundService
{
    double MasterVolume { get; set; }
    bool IsMuted { get; set; }
    void PlayChime();
    void PlayBeep();
    void PlayDingDongDang();
    void PlayBuzzer();
    void PlayFanfare();
    void PlayAttentionChime();
    void PlayWhistle();
    void PlayDrumroll();
    void PlayApplause();
    void StopAll();
}

public class SoundService : ISoundService
{
    private static readonly Random _rand = new();

    private double _masterVolume = 0.8;
    public double MasterVolume
    {
        get => _masterVolume;
        set => _masterVolume = Math.Clamp(value, 0.0, 1.0);
    }

    private bool _isMuted = false;
    public bool IsMuted
    {
        get => _isMuted;
        set
        {
            _isMuted = value;
            if (_isMuted)
            {
                StopAll();
            }
        }
    }

    private double EffectiveVolume => _isMuted ? 0.0 : _masterVolume;

    private readonly object _playbackLock = new();
    private CancellationTokenSource _cts = new();
    private SoundPlayer? _activePlayer;

    public void StopAll()
    {
        lock (_playbackLock)
        {
            try
            {
                _cts.Cancel();
                _cts.Dispose();
                _cts = new CancellationTokenSource();
            }
            catch { }

            try
            {
                _activePlayer?.Stop();
                _activePlayer?.Dispose();
                _activePlayer = null;
            }
            catch { }
        }
    }

    private void PlaySoundSafe(Func<double, byte[]> wavGenerator)
    {
        double vol = EffectiveVolume;
        if (vol <= 0.001) return;

        lock (_playbackLock)
        {
            // Cancel and stop previous sound immediately so sounds never queue up or linger!
            try
            {
                _cts.Cancel();
                _cts.Dispose();
                _cts = new CancellationTokenSource();
                _activePlayer?.Stop();
                _activePlayer?.Dispose();
                _activePlayer = null;
            }
            catch { }

            var token = _cts.Token;
            Task.Run(() =>
            {
                if (token.IsCancellationRequested) return;
                try
                {
                    byte[] wav = wavGenerator(vol);
                    if (token.IsCancellationRequested) return;

                    var ms = new MemoryStream(wav);
                    var sp = new SoundPlayer(ms);

                    lock (_playbackLock)
                    {
                        if (token.IsCancellationRequested)
                        {
                            sp.Dispose();
                            ms.Dispose();
                            return;
                        }
                        _activePlayer = sp;
                    }

                    sp.PlaySync();

                    lock (_playbackLock)
                    {
                        if (_activePlayer == sp) _activePlayer = null;
                        sp.Dispose();
                        ms.Dispose();
                    }
                }
                catch { }
            }, token);
        }
    }

    public void PlayChime() => PlayAttentionChime();

    public void PlayBeep() => PlaySoundSafe(v => GenerateToneWav(new[] { (880.0, 0.15, 0.5) }, masterVol: v));

    public void PlayDingDongDang() => PlaySoundSafe(v => GenerateToneWav(new[]
    {
        (523.25, 0.35, 0.6),
        (659.25, 0.35, 0.6),
        (783.99, 0.60, 0.6)
    }, masterVol: v));

    public void PlayBuzzer() => PlaySoundSafe(v => GenerateBuzzerWav(140.0, 0.6, masterVol: v));

    public void PlayFanfare() => PlaySoundSafe(v => GenerateToneWav(new[]
    {
        (523.25, 0.18, 0.5),
        (659.25, 0.18, 0.5),
        (783.99, 0.18, 0.5),
        (1046.5, 0.70, 0.6)
    }, masterVol: v));

    public void PlayAttentionChime() => PlaySoundSafe(v => GenerateBellWav(1046.5, 1.8, masterVol: v));

    public void PlayWhistle() => PlaySoundSafe(v => GenerateWhistleWav(2800.0, 0.55, masterVol: v));

    public void PlayDrumroll() => PlaySoundSafe(v => GenerateDrumrollWav(2.0, masterVol: v));

    public void PlayApplause() => PlaySoundSafe(v => GenerateApplauseWav(2.5, masterVol: v));

    #region Procedural Audio Synthesizer Helpers

    private static byte[] GenerateToneWav((double Freq, double Duration, double Volume)[] tones, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = 0;
        foreach (var t in tones) totalSamples += (int)(sampleRate * t.Duration);

        WriteWavHeader(bw, totalSamples, sampleRate);

        foreach (var (freq, duration, volume) in tones)
        {
            int samples = (int)(sampleRate * duration);
            for (int i = 0; i < samples; i++)
            {
                double t = (double)i / sampleRate;
                double env = Math.Exp(-t * 4.0); // Exponential decay
                double wave = Math.Sin(2.0 * Math.PI * freq * t) + (0.3 * Math.Sin(4.0 * Math.PI * freq * t));
                short val = (short)(Math.Clamp(wave * volume * env * masterVol, -1.0, 1.0) * 32767);
                bw.Write(val);
            }
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] GenerateBellWav(double fundamental, double duration, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = (int)(sampleRate * duration);
        WriteWavHeader(bw, totalSamples, sampleRate);

        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            double env = Math.Exp(-t * 2.5);
            // Fundamental + 2nd + 3rd harmonic bell overtone
            double wave = (0.6 * Math.Sin(2.0 * Math.PI * fundamental * t))
                        + (0.3 * Math.Sin(2.0 * Math.PI * fundamental * 2.0 * t))
                        + (0.15 * Math.Sin(2.0 * Math.PI * fundamental * 3.0 * t));
            short val = (short)(Math.Clamp(wave * 0.7 * env * masterVol, -1.0, 1.0) * 32767);
            bw.Write(val);
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] GenerateBuzzerWav(double freq, double duration, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = (int)(sampleRate * duration);
        WriteWavHeader(bw, totalSamples, sampleRate);

        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            // Square / Saw buzz wave
            double sin = Math.Sin(2.0 * Math.PI * freq * t);
            double wave = sin >= 0 ? 0.6 : -0.6;
            short val = (short)(wave * 32767 * masterVol);
            bw.Write(val);
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] GenerateWhistleWav(double freq, double duration, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = (int)(sampleRate * duration);
        WriteWavHeader(bw, totalSamples, sampleRate);

        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            double vibrato = 1.0 + (0.05 * Math.Sin(2.0 * Math.PI * 25.0 * t)); // 25Hz trill
            double wave = Math.Sin(2.0 * Math.PI * freq * vibrato * t);
            short val = (short)(wave * 0.55 * 32767 * masterVol);
            bw.Write(val);
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] GenerateDrumrollWav(double duration, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = (int)(sampleRate * duration);
        WriteWavHeader(bw, totalSamples, sampleRate);

        int rollSamples = (int)(sampleRate * (duration - 0.3));
        int tapInterval = sampleRate / 22; // ~22 taps per sec

        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            double sample = 0;

            if (i < rollSamples)
            {
                // Drum taps
                int phase = i % tapInterval;
                double tapT = (double)phase / sampleRate;
                double env = Math.Exp(-tapT * 90.0);
                double intensity = 0.2 + (0.6 * ((double)i / rollSamples)); // crescendo
                sample = (_rand.NextDouble() * 2.0 - 1.0) * env * intensity;
            }
            else
            {
                // Final cymbal / crash hit
                double crashT = (double)(i - rollSamples) / sampleRate;
                double crashEnv = Math.Exp(-crashT * 6.0);
                sample = (_rand.NextDouble() * 2.0 - 1.0) * crashEnv * 0.8;
            }

            short val = (short)(Math.Clamp(sample * masterVol, -1.0, 1.0) * 32767);
            bw.Write(val);
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static byte[] GenerateApplauseWav(double duration, int sampleRate = 44100, double masterVol = 1.0)
    {
        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        int totalSamples = (int)(sampleRate * duration);
        WriteWavHeader(bw, totalSamples, sampleRate);

        for (int i = 0; i < totalSamples; i++)
        {
            double t = (double)i / sampleRate;
            // Envelope: ramp up, sustain, fade out
            double env = 1.0;
            if (t < 0.3) env = t / 0.3;
            else if (t > duration - 0.6) env = (duration - t) / 0.6;

            // Clapping random bursts
            double noise = (_rand.NextDouble() * 2.0 - 1.0);
            double clapImpulse = (_rand.NextDouble() > 0.985) ? 1.5 : 0.4;
            double sample = noise * clapImpulse * env * 0.5;

            short val = (short)(Math.Clamp(sample * masterVol, -1.0, 1.0) * 32767);
            bw.Write(val);
        }

        bw.Flush();
        return ms.ToArray();
    }

    private static void WriteWavHeader(BinaryWriter bw, int totalSamples, int sampleRate)
    {
        int byteRate = sampleRate * 2;
        int dataChunkSize = totalSamples * 2;
        int riffChunkSize = 36 + dataChunkSize;

        bw.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));
        bw.Write(riffChunkSize);
        bw.Write(System.Text.Encoding.ASCII.GetBytes("WAVE"));
        bw.Write(System.Text.Encoding.ASCII.GetBytes("fmt "));
        bw.Write(16); // Subchunk1Size (16 for PCM)
        bw.Write((short)1); // AudioFormat (1 for PCM)
        bw.Write((short)1); // NumChannels (1 = Mono)
        bw.Write(sampleRate);
        bw.Write(byteRate);
        bw.Write((short)2); // BlockAlign
        bw.Write((short)16); // BitsPerSample
        bw.Write(System.Text.Encoding.ASCII.GetBytes("data"));
        bw.Write(dataChunkSize);
    }

    #endregion
}
