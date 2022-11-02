Implementation directories can have arbitrary names.

Inside each implementation directory, any of the following executable files can exist:
- `convert-compat-diff-to-hintful-diff`:<br/>
  Given a valid diff in compat format on stdin, convert it to hintful format and output to stdout.
- `convert-compat-diff-to-unified-diff`:<br/>
  Given a valid diff in compat format on stdin, convert it to unified format and output to stdout.
- `convert-hintful-diff-to-compat-diff`:<br/>
  Given a valid diff in hintful format on stdin, convert it to compat format and output to stdout.
- `convert-hintful-diff-to-unified-diff`:<br/>
  Given a valid diff in hintful format on stdin, convert it to unified format and output to stdout.
- `convert-unified-diff-to-compat-diff`:<br/>
  Given a valid diff in unified format on stdin, convert it to compat format and output to stdout.
- `convert-unified-diff-to-hintful-diff`:<br/>
  Given a valid diff in unified format on stdin, convert it to hintful format and output to stdout.
- `diff-hintful`:<br/>
  Given two directories as arguments, produce a diff in hintful format and output to stdout.
- `diff-unified`:<br/>
  Given two directories as arguments, produce a diff in unified format and output to stdout.
- `patch-unified`:<br/>
  Given a valid diff in unified format on stdin and a directory name as the first argument, apply the changes to that directory.
- `reverse-compat-diff`:<br/>
  Given a valid diff in compat format on stdin, reverse it and output to stdout.
- `reverse-hintful-diff`:<br/>
  Given a valid diff in hintful format on stdin, reverse it and output to stdout.
- `reverse-unified-diff`:<br/>
  Given a valid diff in unified format on stdin, reverse it and output to stdout.
- `terminal-highlight-diff`:<br/>
  Given a valid diff on stdin that contains no terminal control codes, add terminal control codes to highlight it and output to stdout.
- `terminal-visualize-diff`:<br/>
  Given a valid diff on stdin that contains no terminal control codes, create a visualization of it using terminal control codes.
- `validate-compat-diff`:<br/>
  Given a file on stdin, determine whether it is a valid diff in compat format and set the exit code accordingly.
- `validate-hintful-diff`:<br/>
  Given a file on stdin, determine whether it is a valid diff in hintful format and set the exit code accordingly.
- `validate-unified-diff`:<br/>
  Given a file on stdin, determine whether it is a valid diff in unified format and set the exit code accordingly.
