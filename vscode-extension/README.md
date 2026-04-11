# vibescore VS Code Extension

Show vibescore warnings inline in your editor.

## Features

- **Inline decorations**: Underline problematic code with severity colors
- **Quick-fix suggestions**: Hover over issues for fix recommendations
- **Status bar**: Current file/project grade at a glance
- **Problems panel**: All vibescore issues as VS Code diagnostics

## Requirements

- Python 3.9+ with `vibescore` installed (`pip install vibescore`)
- VS Code 1.80+

## Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `vibescore.pythonPath` | string | `"python"` | Python interpreter path |
| `vibescore.autoScan` | boolean | `true` | Scan on file save |
| `vibescore.minSeverity` | string | `"warning"` | Minimum severity to show |

## Development

```bash
cd vscode-extension
npm install
npm run compile
# F5 to launch Extension Development Host
```
