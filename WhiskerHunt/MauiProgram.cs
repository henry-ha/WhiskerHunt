namespace WhiskerHunt;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder.UseMauiApp<App>()
               .ConfigureFonts(fonts =>
               {
                   // The game UI uses device-native system fonts.
               });
#if ANDROID
        // IndexedDB and DOM storage keep catches available across launches.
        Microsoft.Maui.Handlers.WebViewHandler.Mapper.AppendToMapping("WhiskerHuntStorage", (handler, _) =>
        {
            handler.PlatformView.Settings.JavaScriptEnabled = true;
            handler.PlatformView.Settings.DomStorageEnabled = true;
            handler.PlatformView.Settings.DatabaseEnabled = true;
            // Preserve MAUI's native file picker while handling only local
            // camera-video permission requests for the live encounter.
            handler.PlatformView.SetWebChromeClient(new WhiskerWebChromeClient(handler));
        });
#endif
        return builder.Build();
    }
}
