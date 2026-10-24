from pathlib import Path
p=Path('/mnt/data/hush_v3111/WhiskerHunt/Platforms/Android/HushArCoreActivity.cs')
t=p.read_text()
t=t.replace('private bool _placementReady;', 'private bool _placementReady;\n    // Screen-locked preview is explicitly NOT a world-tracked AR anchor.\n    private bool _previewPlaced;')
t=t.replace('top.SetPadding(Dp(16), Dp(34), Dp(16), Dp(10));','top.SetPadding(Dp(16), Dp(26), Dp(16), Dp(8));')
t=t.replace('Text = "Hush Hunt · ARCore Safari ✨", TextSize = 22','Text = "AR Safari ✨", TextSize = 19')
t=t.replace('var tip = new TextView(this) { Text = "Google Play Services for AR (ARCore) · Google privacy policy applies. No recording until Collect.", TextSize = 11 };','var tip = new TextView(this) { Text = "Tracked when possible · screen preview otherwise. Private photo on Capture.", TextSize = 11 };')
t=t.replace('Text = "🧭 Place", Enabled = false','Text = "🐾 Place", Enabled = true')
t=t.replace('bottom.SetPadding(Dp(9), Dp(10), Dp(9), Dp(38));','bottom.SetPadding(Dp(9), Dp(9), Dp(9), Dp(32));')
start=t.index('    private void PlaceAtCenter()')
end=t.index('    internal void UpdatePlacementReady',start)
t=t[:start]+'''    private void PlaceAtCenter()
    {
        if (_renderer is null || _surface is null) return;
        // Try a real ARCore plane first. If ARCore cannot resolve one, a screen-locked
        // preview is offered instead of blocking the child from playing at all.
        _renderer.QueuePlacement(_surface.Width / 2f, _surface.Height * .62f, true);
    }

    internal void PreviewPlace(float x, float y)
    {
        RunOnUiThread(() =>
        {
            if (_anchor is not null || _surface is null || _creature is null) return;
            _previewPlaced = true;
            int w = Dp(164);
            _creature.LayoutParameters = new LayoutParams(w, w, GravityFlags.Top | GravityFlags.Left);
            _creature.TranslationX = Math.Clamp(x - w / 2f, 0, Math.Max(0,_surface.Width - w));
            _creature.TranslationY = Math.Clamp(y - w, 0, Math.Max(0,_surface.Height - w));
            _creature.Visibility = ViewStates.Visible;
            if (_collect is not null) _collect.Enabled = true;
            if (_place is not null) { _place.Enabled = true; _place.Text = "🐾 Move"; }
            SetStatus("Preview placed on screen (not world-tracked). Tap another spot to move, or Capture. For anchored AR, scan a textured floor.");
        });
    }

'''+t[end:]
t=t.replace('if (ready == _placementReady) return;', 'if (ready == _placementReady && _place?.Enabled == true) return;')
t=t.replace('if (_place is not null && _anchor is null) _place.Enabled = ready;', 'if (_place is not null && _anchor is null) _place.Enabled = true;')
t=t.replace('''                    : "Scan a well-lit floor or table slowly. A surface may appear near the bottom of the screen; you can also tap it directly.");''', '''                    : "Tap Place or the camera to add a preview. Scan a floor for world-tracked placement.");''')
t=t.replace('''            _anchor = anchor;
            if (_creature is not null)''','''            _anchor = anchor;
            _previewPlaced = false;
            if (_creature is not null)''')
t=t.replace('''            if (!tracking)
            {
                _creature.Visibility = ViewStates.Invisible;
                return;
            }''','''            if (!tracking)
            {
                if (!_previewPlaced) _creature.Visibility = ViewStates.Invisible;
                return;
            }''')
t=t.replace('''if (_capturePending || _surface is null || _art is null || _anchor is null) return;''','''if (_capturePending || _surface is null || _art is null || (_anchor is null && !_previewPlaced)) return;''')
t=t.replace('''FinishWith("captured", "ARCore surface encounter.",''','''FinishWith("captured", _previewPlaced ? "Screen-locked preview, not world-anchored AR." : "ARCore surface encounter.",''')
t=t.replace('''                    if (!anchored) _host.SetStatus("No tracked plane at that spot. Point toward a textured floor or table, move slowly and tap the surface. Or use 2D Safari.");''','''                    if (!anchored) _host.PreviewPlace(x.Value,y.Value);''')
p.write_text(t)
print('Native AR patched',t.count('PreviewPlace'),t.count('_previewPlaced'))
