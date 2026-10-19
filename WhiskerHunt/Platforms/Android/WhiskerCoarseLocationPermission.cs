using Microsoft.Maui.ApplicationModel;

namespace WhiskerHunt;

/// <summary>
/// Ask for approximate foreground location alone. This avoids interpreting an
/// Android 12+ approximate-only grant as a failure of a fine/coarse group.
/// There is deliberately no background or precise-location requirement.
/// </summary>
internal sealed class WhiskerCoarseLocationPermission : Permissions.BasePlatformPermission
{
    public override (string androidPermission, bool isRuntime)[] RequiredPermissions =>
        new[] { (Android.Manifest.Permission.AccessCoarseLocation, true) };
}
