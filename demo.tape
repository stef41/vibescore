# VHS tape file — https://github.com/charmbracelet/vhs
# Run: vhs demo.tape
# Produces: demo.gif

Output demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 900
Set Height 600
Set Theme "Monokai"
Set Padding 20

Type "# Grade your project in one command"
Enter
Sleep 500ms

Type "pip install vibescore"
Enter
Sleep 2s

Type "vibescore ."
Enter
Sleep 4s

Type "# Generate a CI workflow automatically"
Enter
Sleep 500ms

Type "vibescore --init-ci"
Enter
Sleep 2s

Type "# Watch mode — re-scan on every change"
Enter
Sleep 500ms

Type "vibescore --watch"
Enter
Sleep 3s
