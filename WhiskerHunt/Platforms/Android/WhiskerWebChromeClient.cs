using Android.Content.PM;
using Android.Webkit;
using Microsoft.Maui.Handlers;
using Microsoft.Maui.Platform;

namespace WhiskerHunt;

/// <summary>
/// Allows only camera-video capture for the app's bundled local UI, and only
/// after Android has granted the app CAMERA permission. No microphone, screen
/// recording, or arbitrary web origins are granted access.
/// </summary>
internal sealed class WhiskerWebChromeClient : MauiWebChromeClient
{
    public WhiskerWebChromeClient(IWebViewHandler handler) : base(handler) { }

    public override void OnPermissionRequest(PermissionRequest? request)
    {
        if (request is null) return;
        var origin = request.Origin;
        var localUi = origin is not null &&
            (string.Equals(origin.Scheme, "file", StringComparison.OrdinalIgnoreCase) ||
             (string.Equals(origin.Scheme, "https", StringComparison.OrdinalIgnoreCase) &&
              string.Equals(origin.Host, "appassets.androidplatform.net", StringComparison.OrdinalIgnoreCase)));
        var resources = request.GetResources();
        var cameraOnly = resources is { Length: 1 } &&
            string.Equals(resources[0], PermissionRequest.ResourceVideoCapture, StringComparison.OrdinalIgnoreCase);
        var permissionGranted = Android.App.Application.Context.CheckSelfPermission(Android.Manifest.Permission.Camera)
            == Permission.Granted;

        if (localUi && cameraOnly && permissionGranted)
            request.Grant(new[] { PermissionRequest.ResourceVideoCapture });
        else
            request.Deny();
    }
}
