# HTML Preview Watch

`install.sh` installs this helper for Linux desktop and Remote SSH VS Code.
It adds a non-recursive watcher while each HTML document is open, then removes
it when the document closes. VS Code reloads clean documents after external
writes; the existing HTML preview refreshes from those document events. Unsaved
edits remain protected. Recursive workspace watching stays disabled.

Linked CSS, JavaScript, and images do not get additional watchers.

`extension_test.js` runs in a real VS Code extension test host with this helper
and `george-alisson.html-preview-vscode` loaded through
`--extensionDevelopmentPath`. Use an isolated `--user-data-dir`,
`--extensions-dir`, and scratch workspace under an ignored project directory;
pass the test file through `--extensionTestsPath`. It checks preview updates
after external writes and atomic replacement, plus protection of unsaved edits.
