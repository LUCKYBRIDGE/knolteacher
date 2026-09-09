using KnolTeacher.Desktop.Views.Controls;
using Xunit;

namespace KnolTeacher.Tests;

public class NolboardWidgetRegistryTests
{
    private static readonly string[] WidgetTypes =
    {
        "timer",
        "picker",
        "dice",
        "wheel",
        "score",
        "drawing",
        "timetable",
        "meal",
        "memo",
        "checklist",
        "qr",
        "weather",
        "dday"
    };

    [Fact]
    public void Registry_ContainsExactlyTheSupportedInCanvasWidgetKinds()
    {
        foreach (string type in WidgetTypes)
        {
            Assert.True(WidgetRegistry.TryGet(type, out var definition));
            Assert.Equal(type, definition.Type);
            Assert.True(definition.DefaultWidth >= definition.MinWidth);
            Assert.True(definition.DefaultHeight >= definition.MinHeight);
            Assert.True(definition.CanResize);
        }
    }

    [Fact]
    public void Pinball_IsASeparateWindowTool_NotANolboardWidget()
    {
        Assert.False(WidgetRegistry.TryGet("pinball", out _));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("unknown")]
    public void UnknownWidgetKinds_AreRejected(string? type)
    {
        Assert.False(WidgetRegistry.TryGet(type, out _));
    }
}
