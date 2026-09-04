using System;
using System.Media;
using System.Threading.Tasks;

namespace KnolTeacher.Desktop.Services;

public interface ISoundService
{
    void PlayChime();
    void PlayBeep();
}

public class SoundService : ISoundService
{
    public void PlayChime()
    {
        Task.Run(() =>
        {
            try
            {
                SystemSounds.Asterisk.Play();
            }
            catch { }
        });
    }

    public void PlayBeep()
    {
        Task.Run(() =>
        {
            try
            {
                Console.Beep(880, 300);
            }
            catch { }
        });
    }
}
