"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const child_process_1 = require("child_process");
let statusBarItem;
let diagnosticCollection;
function activate(context) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 99);
    statusBarItem.command = "vibescore.scanProject";
    statusBarItem.text = "$(star) vibescore";
    statusBarItem.tooltip = "Click to grade project";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    diagnosticCollection =
        vscode.languages.createDiagnosticCollection("vibescore");
    context.subscriptions.push(diagnosticCollection);
    context.subscriptions.push(vscode.commands.registerCommand("vibescore.scanProject", async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders) {
            vscode.window.showWarningMessage("No workspace folder open");
            return;
        }
        await scanProject(folders[0].uri.fsPath);
    }));
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async () => {
        const config = vscode.workspace.getConfiguration("vibescore");
        if (!config.get("autoScan"))
            return;
        const folders = vscode.workspace.workspaceFolders;
        if (folders) {
            await scanProject(folders[0].uri.fsPath);
        }
    }));
}
async function scanProject(rootPath) {
    const config = vscode.workspace.getConfiguration("vibescore");
    const pythonPath = config.get("pythonPath") || "python";
    const minSeverity = config.get("minSeverity") || "warning";
    statusBarItem.text = "$(loading~spin) Scanning...";
    try {
        const stdout = await new Promise((resolve, reject) => {
            const proc = (0, child_process_1.spawn)(pythonPath, [
                "-m",
                "vibescore",
                rootPath,
                "--format",
                "json",
            ]);
            let out = "";
            let err = "";
            proc.stdout.on("data", (chunk) => {
                out += chunk.toString();
            });
            proc.stderr.on("data", (chunk) => {
                err += chunk.toString();
            });
            proc.on("close", (code) => {
                if (code === 0 || out.trim().startsWith("{")) {
                    resolve(out);
                }
                else {
                    reject(new Error(err || `vibescore exited with code ${code}`));
                }
            });
            proc.on("error", reject);
        });
        const report = JSON.parse(stdout);
        // Update status bar
        const grade = report.overall_grade;
        const icon = grade.startsWith("A") ? "$(pass)" :
            grade.startsWith("B") ? "$(info)" :
                grade.startsWith("C") ? "$(warning)" : "$(error)";
        statusBarItem.text = `${icon} ${grade}`;
        statusBarItem.tooltip = `vibescore: ${grade} (${report.overall_score.toFixed(1)}/100)`;
        // Map issues to diagnostics
        diagnosticCollection.clear();
        const diagMap = new Map();
        const severityOrder = ["critical", "warning", "info"];
        const minIdx = severityOrder.indexOf(minSeverity);
        for (const cat of report.categories) {
            for (const issue of cat.issues) {
                const sevIdx = severityOrder.indexOf(issue.severity);
                if (sevIdx > minIdx)
                    continue;
                if (!issue.file)
                    continue;
                const filePath = vscode.Uri.joinPath(vscode.Uri.file(rootPath), issue.file).fsPath;
                const line = Math.max((issue.line || 1) - 1, 0);
                const range = new vscode.Range(line, 0, line, 1000);
                const severity = issue.severity === "critical"
                    ? vscode.DiagnosticSeverity.Error
                    : issue.severity === "warning"
                        ? vscode.DiagnosticSeverity.Warning
                        : vscode.DiagnosticSeverity.Information;
                const diag = new vscode.Diagnostic(range, `[${issue.code}] ${issue.message}`, severity);
                diag.source = "vibescore";
                const existing = diagMap.get(filePath) || [];
                existing.push(diag);
                diagMap.set(filePath, existing);
            }
        }
        for (const [filePath, diags] of diagMap) {
            diagnosticCollection.set(vscode.Uri.file(filePath), diags);
        }
        vscode.window.showInformationMessage(`vibescore: ${grade} (${report.overall_score.toFixed(1)}/100)`);
    }
    catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        statusBarItem.text = "$(error) vibescore";
        vscode.window.showErrorMessage(`vibescore error: ${msg}`);
    }
}
function deactivate() {
    diagnosticCollection?.dispose();
}
//# sourceMappingURL=extension.js.map