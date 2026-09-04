using System;
using System.Collections.Generic;
using System.Windows.Interop;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IGlobalHotkeyService : IDisposable
{
    event Action<string>? HotkeyPressed;
    void Initialize();
    void ReloadHotkeys();
}

public class GlobalHotkeyService : IGlobalHotkeyService
{
    private readonly IConfigService _configService;
    private HwndSource? _hwndSource;
    private readonly Dictionary<int, string> _hotkeyActionMap = new();

    public event Action<string>? HotkeyPressed;

    public GlobalHotkeyService(IConfigService configService)
    {
        _configService = configService;
    }

    public void Initialize()
    {
        if (_hwndSource != null) return;

        // Create a hidden message-only window for receiving WM_HOTKEY
        var parameters = new HwndSourceParameters("KnolTeacherHotkeyListener")
        {
            Width = 0,
            Height = 0,
            PositionX = 0,
            PositionY = 0,
            WindowStyle = 0x800000 // WS_BORDER
        };

        _hwndSource = new HwndSource(parameters);
        _hwndSource.AddHook(HwndHook);

        RegisterAll();
    }

    public void ReloadHotkeys()
    {
        UnregisterAll();
        RegisterAll();
    }

    private void RegisterAll()
    {
        if (_hwndSource == null) return;

        IntPtr handle = _hwndSource.Handle;
        var hotkeys = _configService.Hotkeys;

        foreach (var item in hotkeys)
        {
            if (!item.Enabled) continue;

            uint mod = ParseModifier(item.Modifier);
            uint vk = ParseVirtualKey(item.Key);

            if (vk != 0)
            {
                bool success = NativeMethods.RegisterHotKey(handle, item.Id, mod | NativeMethods.MOD_NOREPEAT, vk);
                if (success)
                {
                    _hotkeyActionMap[item.Id] = item.Action;
                }
            }
        }
    }

    private void UnregisterAll()
    {
        if (_hwndSource == null) return;

        IntPtr handle = _hwndSource.Handle;
        foreach (var id in _hotkeyActionMap.Keys)
        {
            NativeMethods.UnregisterHotKey(handle, id);
        }
        _hotkeyActionMap.Clear();
    }

    private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == NativeMethods.WM_HOTKEY)
        {
            int hotkeyId = wParam.ToInt32();
            if (_hotkeyActionMap.TryGetValue(hotkeyId, out string? action) && !string.IsNullOrEmpty(action))
            {
                HotkeyPressed?.Invoke(action);
                handled = true;
            }
        }
        return IntPtr.Zero;
    }

    private static uint ParseModifier(string mod) => mod switch
    {
        "Alt" => NativeMethods.MOD_ALT,
        "Ctrl" => NativeMethods.MOD_CONTROL,
        "Ctrl+Alt" => NativeMethods.MOD_CONTROL | NativeMethods.MOD_ALT,
        "Shift+Alt" => NativeMethods.MOD_SHIFT | NativeMethods.MOD_ALT,
        "None" => 0,
        _ => NativeMethods.MOD_ALT
    };

    private static uint ParseVirtualKey(string key)
    {
        key = key.Trim().ToUpperInvariant();

        // 0-9
        if (key.Length == 1 && key[0] >= '0' && key[0] <= '9')
            return (uint)key[0];

        // A-Z
        if (key.Length == 1 && key[0] >= 'A' && key[0] <= 'Z')
            return (uint)key[0];

        // Function keys F1-F12
        return key switch
        {
            "F1" => 0x70,
            "F2" => 0x71,
            "F3" => 0x72,
            "F4" => 0x73,
            "F5" => 0x74,
            "F6" => 0x75,
            "F7" => 0x76,
            "F8" => 0x77,
            "F9" => 0x78,
            "F10" => 0x79,
            "F11" => 0x7A,
            "F12" => 0x7B,
            _ => 0
        };
    }

    public void Dispose()
    {
        UnregisterAll();
        if (_hwndSource != null)
        {
            _hwndSource.RemoveHook(HwndHook);
            _hwndSource.Dispose();
            _hwndSource = null;
        }
    }
}
