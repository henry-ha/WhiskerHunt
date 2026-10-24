# v3.9.3 verification

- Source signature now explicitly uses `Google.AR.Core.Frame`.
- Call site passes the ARCore session frame from `session.Update()`.
- No unqualified `Frame` type in `HushArCoreActivity.cs`.
- Application ID, collection keys and backup names unchanged.
- Android/browser versioned JavaScript and CSS resources are identical.
- JavaScript syntax and ZIP integrity checked.
- An Android compile could not be performed here; on-device performance and warnings have not been independently verified.
