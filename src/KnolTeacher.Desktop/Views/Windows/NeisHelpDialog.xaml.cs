using System.Windows;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class NeisHelpDialog : Window
{
    public NeisHelpDialog()
    {
        InitializeComponent();
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }
}