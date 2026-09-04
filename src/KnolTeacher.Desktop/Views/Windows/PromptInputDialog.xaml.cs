using System.Windows;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class PromptInputDialog : Window
{
    public string InputText => TbInput.Text.Trim();

    public PromptInputDialog(string title, string prompt, string defaultValue = "")
    {
        InitializeComponent();
        Title = title;
        TxtPrompt.Text = prompt;
        TbInput.Text = defaultValue;
        TbInput.SelectAll();
        Loaded += (s, e) => TbInput.Focus();
    }

    private void BtnOk_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = true;
        Close();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
