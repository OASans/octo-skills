const vscode = require('vscode');
const path = require('path');

function activate(context) {
    const watchers = new Map();

    function watch(document) {
        if (document.languageId !== 'html' ||
            !['file', 'vscode-remote'].includes(document.uri.scheme)) {
            return;
        }
        const key = document.uri.toString();
        if (watchers.has(key)) {
            return;
        }
        const directory = document.uri.with({
            path: path.posix.dirname(document.uri.path), query: '', fragment: ''
        });
        const filename = path.posix.basename(document.uri.path)
            .replace(/([*?\[\]{}])/g, '[$1]');
        // A filename-only RelativePattern installs a non-recursive watcher.
        // Its file events also reload VS Code's clean document model, which
        // makes the existing HTML preview refresh after external writes.
        watchers.set(key, vscode.workspace.createFileSystemWatcher(
            new vscode.RelativePattern(directory, filename)
        ));
    }

    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument(watch),
        vscode.workspace.onDidCloseTextDocument(document => {
            const key = document.uri.toString();
            watchers.get(key)?.dispose();
            watchers.delete(key);
        }),
        { dispose() {
            for (const watcher of watchers.values()) {
                watcher.dispose();
            }
            watchers.clear();
        } }
    );
    for (const document of vscode.workspace.textDocuments) {
        watch(document);
    }
}

exports.activate = activate;
