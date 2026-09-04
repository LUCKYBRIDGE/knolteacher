using System.Linq;
using System.Windows;
using System.Windows.Controls;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class AddSiteBookmarkDialog : Window
{
    public string SiteTitle { get; private set; } = string.Empty;
    public string SiteUrl { get; private set; } = string.Empty;
    public string SiteDesc { get; private set; } = string.Empty;
    public string SiteIcon { get; private set; } = "⭐";
    public string SelectedIcon => SiteIcon;

    public AddSiteBookmarkDialog()
    {
        InitializeComponent();
        TbTitle.Focus();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void BtnAdd_Click(object sender, RoutedEventArgs e)
    {
        string title = TbTitle.Text.Trim();
        string url = TbUrl.Text.Trim();

        if (string.IsNullOrWhiteSpace(title))
        {
            MessageBox.Show("사이트 이름을 입력해주세요.", "입력 확인", MessageBoxButton.OK, MessageBoxImage.Warning);
            TbTitle.Focus();
            return;
        }

        if (string.IsNullOrWhiteSpace(url) || url == "https://")
        {
            MessageBox.Show("올바른 웹사이트 URL을 입력해주세요.", "입력 확인", MessageBoxButton.OK, MessageBoxImage.Warning);
            TbUrl.Focus();
            return;
        }

        SiteTitle = title;
        SiteUrl = url;
        SiteDesc = TbDesc.Text.Trim();

        foreach (var child in PnlIcons.Children)
        {
            if (child is RadioButton rb && rb.IsChecked == true)
            {
                SiteIcon = rb.Content?.ToString() ?? "⭐";
                break;
            }
        }

        DialogResult = true;
        Close();
    }
}
