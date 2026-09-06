using System;
using System.Threading.Tasks;

namespace KnolTeacher.Desktop.Services;

public interface ITtsService
{
    bool IsSpeaking { get; }
    event Action<bool>? SpeakingStateChanged;
    Task SpeakAsync(string text, int rate = 0, int volume = 100);
    void Stop();
}
