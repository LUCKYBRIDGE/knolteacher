using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MemoWidgetView : UserControl
{
    private readonly string _memoFile;

    public MemoWidgetView(IConfigService? configService = null)
    {
        InitializeComponent();

        string dir = configService?.ConfigDir ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _memoFile = Path.Combine(dir, "board_memo.txt");

        Loaded += (s, e) =>
        {
            if (File.Exists(_memoFile))
            {
                try { TbMemo.Text = File.ReadAllText(_memoFile); } catch { }
            }
            else
            {
                TbMemo.Text = "• [알림] 오늘 5교시는 음악실에서 수업합니다.\n• [준비물] 수학익힘책 42쪽 풀어오기\n• [과제] 주말 독서록 작성하기";
            }
        };

        TbMemo.TextChanged += (s, e) =>
        {
            try { File.WriteAllText(_memoFile, TbMemo.Text); } catch { }
        };
    }

    private void BtnInsertTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            if (!string.IsNullOrEmpty(TbMemo.Text) && !TbMemo.Text.EndsWith("\n"))
            {
                TbMemo.AppendText("\n");
            }
            TbMemo.AppendText(tag);
            TbMemo.CaretIndex = TbMemo.Text.Length;
            TbMemo.Focus();
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("알림장 내용을 모두 지우시겠습니까?", "알림장 비우기", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            TbMemo.Clear();
            try { File.WriteAllText(_memoFile, ""); } catch { }
        }
    }
}
