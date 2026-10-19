"""Static regression checks for the v3.7.1 Android compile hotfix.

These are source-level checks, not a substitute for MSBuild or device testing.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAUI = ROOT / 'WhiskerHunt'


class CompilationHotfixTests(unittest.TestCase):
    def test_android_debug_is_unambiguous(self):
        source = (MAUI / 'Platforms/Android/AndroidApproximateLocationProvider.cs').read_text()
        self.assertIn('using DiagnosticDebug = System.Diagnostics.Debug;', source)
        self.assertEqual(source.count('DiagnosticDebug.WriteLine('), 5)
        self.assertIsNone(re.search(r'(?<!\w)Debug\.WriteLine\(', source))
        self.assertNotIn('using System.Diagnostics;', source)

    def test_webchromeclient_nullable_parameter_is_guarded(self):
        source = (MAUI / 'Platforms/Android/WhiskerWebChromeClient.cs').read_text()
        self.assertIn('OnPermissionRequest(PermissionRequest? request)', source)
        self.assertIn('if (request is null) return;', source)
        self.assertIn('request.Grant(', source)
        self.assertIn('request.Deny()', source)

    def test_version_assets_and_project_consistent(self):
        project = (MAUI / 'WhiskerHunt.csproj').read_text()
        self.assertIn('<ApplicationDisplayVersion>3.7.1</ApplicationDisplayVersion>', project)
        self.assertIn('<ApplicationVersion>40</ApplicationVersion>', project)
        self.assertIn('ApplicationId>uk.whiskerhunt.mobile</ApplicationId>', project)
        self.assertIn('Source="index_v40.html"', (MAUI / 'MainPage.xaml').read_text())
        for folder in (ROOT / 'BrowserPreview', MAUI / 'Resources/Raw'):
            entry = (folder / 'index_v40.html').read_text()
            self.assertIn('app_v40.js', entry)
            self.assertIn('style_v40.css', entry)
            self.assertIn('3.7.1-40', entry)
            self.assertIn("const WHISKER_BUILD='3.7.1', WHISKER_BUILD_NUMBER=40;",
                          (folder / 'app_v40.js').read_text())
            self.assertEqual((folder / 'app_v40.js').read_bytes(), (MAUI / 'Resources/Raw/app_v40.js').read_bytes())
            self.assertIn('whisker-hunt-shell-v40', (folder / 'sw.js').read_text())
        solution = (ROOT / 'WhiskerHunt.sln').read_text()
        self.assertIn('WhiskerHunt\\WhiskerHunt.csproj', solution)
        self.assertIn('.Debug|Any CPU.Deploy.0', solution)

    def test_native_storage_schema_not_changed(self):
        # MainPage bridge stays identical in this C# compile-only hotfix.
        source = (MAUI / 'MainPage.xaml.cs').read_text()
        self.assertIn('whisker-hunt-state.json', source)
        self.assertIn('BackupStatePath => StatePath + ".bak"', source)
        self.assertIn('AndroidApproximateLocationProvider.TryGetAsync', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
