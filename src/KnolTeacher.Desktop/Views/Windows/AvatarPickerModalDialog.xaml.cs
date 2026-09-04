using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class AvatarPickerModalDialog : Window
{
    public string SelectedAvatarId { get; private set; } = string.Empty;

    public AvatarPickerModalDialog(StudentItem? student = null)
    {
        InitializeComponent();

        if (student != null)
        {
            TxtHeaderTitle.Text = $"[{student.Number}번 {student.Name}] 동물 아바타 선택";
            TxtStudentDesc.Text = "아래 32종의 동물 중 마음에 드는 아바타를 클릭하면 즉시 적용됩니다.";
            SelectedAvatarId = student.EffectiveAvatarId;
            try
            {
                ImgCurrentAvatar.Source = new BitmapImage(new Uri(student.AvatarUri, UriKind.RelativeOrAbsolute));
            }
            catch { }
        }
        else
        {
            SelectedAvatarId = "avatar_01";
        }

        ItemsAvatars.ItemsSource = AnimalAvatarCatalog.Avatars;
    }

    private void AvatarCard_Click(object sender, MouseButtonEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.DataContext is AnimalAvatarInfo info)
        {
            SelectedAvatarId = info.Id;
            DialogResult = true;
            Close();
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
