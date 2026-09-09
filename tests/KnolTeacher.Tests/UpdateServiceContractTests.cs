using KnolTeacher.Desktop.Services;
using Xunit;

namespace KnolTeacher.Tests;

public class UpdateServiceContractTests
{
    [Theory]
    [InlineData("KnolTeacher.exe", true)]
    [InlineData("knolteacher.EXE", true)]
    [InlineData("놀티쳐.exe", true)]
    [InlineData("default.exe", false)]
    [InlineData("setup.exe", false)]
    [InlineData("", false)]
    public void AcceptedReleaseAssetNames_AreExplicitAndLimited(string assetName, bool expected)
    {
        Assert.Equal(expected, UpdateService.IsAcceptedReleaseAssetName(assetName));
    }

    [Theory]
    [InlineData("v3.0.9", "v3.0.8", true)]
    [InlineData("v3.0.8", "v3.0.8", false)]
    [InlineData("v3.0.7", "v3.0.8", false)]
    public void VersionComparison_UsesSemanticVersionOrdering(string latest, string current, bool expected)
    {
        Assert.Equal(expected, UpdateService.IsNewerVersion(latest, current));
    }

    [Theory]
    [InlineData("v3.0.9", "3.0.9.0", true)]
    [InlineData("3.0.9", "v3.0.9", true)]
    [InlineData("v3.0.9", "v3.0.8", false)]
    [InlineData("invalid", "v3.0.9", false)]
    public void SameProductVersion_UsesMajorMinorBuild(string left, string right, bool expected)
    {
        Assert.Equal(expected, UpdateService.IsSameProductVersion(left, right));
    }
}
