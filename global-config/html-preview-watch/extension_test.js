const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vscode = require('vscode');

// Run in an isolated VS Code extension test host with both this extension and
// george-alisson.html-preview-vscode enabled and workspace watching excluded.
async function run() {
    const folder = vscode.workspace.workspaceFolders[0].uri;
    const uri = vscode.Uri.joinPath(folder, 'preview [check].html');
    fs.writeFileSync(uri.fsPath, '<html><body>before</body></html>');
    await vscode.workspace.getConfiguration('files').update(
        'watcherExclude', { '**': true }, vscode.ConfigurationTarget.Workspace
    );
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document);
    await vscode.extensions.getExtension('octo.html-preview-watch').activate();
    const previewExtension = vscode.extensions.getExtension('george-alisson.html-preview-vscode');
    await previewExtension.activate();
    const { HTMLPreview } = require(path.join(previewExtension.extensionPath, 'out/features/preview.js'));
    const originalUpdate = HTMLPreview.prototype.doUpdate;
    let rendered;
    let timeout;
    function expectPreview(marker) {
        return new Promise((resolve, reject) => {
            rendered = preview => {
                if (preview.editor.webview.html.includes(marker)) {
                    clearTimeout(timeout);
                    rendered = undefined;
                    resolve();
                }
            };
            timeout = setTimeout(() => reject(new Error(`Preview did not refresh: ${marker}; document: ${document.getText()}`)), 10000);
        });
    }
    HTMLPreview.prototype.doUpdate = async function (...args) {
        await originalUpdate.apply(this, args);
        rendered?.(this);
    };
    try {
        const initial = expectPreview('before');
        await vscode.commands.executeCommand('html.showPreviewToSide', uri);
        await initial;
        // VS Code batches watch registration asynchronously.
        await new Promise(resolve => setTimeout(resolve, 500));

        const first = expectPreview('external-first');
        fs.writeFileSync(uri.fsPath, '<html><body>external-first</body></html>');
        await first;
        assert(document.getText().includes('external-first'));

        const second = expectPreview('external-replaced');
        const replacement = `${uri.fsPath}.new`;
        fs.writeFileSync(replacement, '<html><body>external-replaced</body></html>');
        fs.renameSync(replacement, uri.fsPath);
        await second;
        assert(document.getText().includes('external-replaced'));

        const edit = new vscode.WorkspaceEdit();
        edit.insert(uri, new vscode.Position(0, 0), '<!-- unsaved -->');
        await vscode.workspace.applyEdit(edit);
        fs.writeFileSync(uri.fsPath, '<html><body>external-while-dirty</body></html>');
        await new Promise(resolve => setTimeout(resolve, 600));
        assert(document.isDirty);
        assert(document.getText().startsWith('<!-- unsaved -->'));
        assert(!document.getText().includes('external-while-dirty'));
        console.log('PASS: HTML preview refreshes after external writes and atomic replacement; unsaved edits survive.');
    } finally {
        clearTimeout(timeout);
        HTMLPreview.prototype.doUpdate = originalUpdate;
    }
}

exports.run = run;
