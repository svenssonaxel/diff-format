Test directories are three-digit numbers.

Filename schema inside test directories:
- `/[a-z]/`:
  A directory containing a version of data
- `<NN>-<A>-<B>.<TYPE>.diff`:
  A diff file comparing versions `<A>` and `<B>`.
  `<NN>` is for ordering.
  `<TYPE>` can be:
  - `compat`: A correct compat diff format file.
  - `hintful`: A correct hintful diff format file.
  - `unified`: A correct unified diff format file.
  - `invalid.compat`: A file that should not pass validation for compat diff format.
  - `invalid.hintful`: A file that should not pass validation for hintful diff format.
  - `invalid.unified`: A file that should not pass validation for unified diff format.

Test directories and what they focus on, files and what they test:
- `001/`:
  A simple example.
  - `a/`:
    Before change.
  - `b/`:
    After change.
  - `01-a-b.hintful.diff`:
    Simple minimized example, uses `#` for intermediate state.
  - `03-a-b.hintful.diff`:
    Less than minimized example.
  - `04-a-b.unified.diff`:
    More readable line ordering.
  - `05-a-b.unified.diff`:
    Simple example.
  - `07-a-b.hintful.diff`:
    Two-step change using a snippet for intermediate state.
  - `08-a-b.invalid.hintful.diff`:
    No end of file before hunk is done.
  - `09-a-b.invalid.hintful.diff`:
    Hunk line count must be correct.
  - `10-a-b.invalid.hintful.diff`:
    Snippets must end within hunk.
  - `11-a-b.invalid.hintful.diff`:
    Snippet content must be consistent between invocations.
  - `12-a-b.invalid.hintful.diff`:
    Content line count must be correct.
- `002/`:
  File-level operations and CR handling.
  - `a/`:
    Before change.
    - `add-cr`:
      Contains a `\n` that will be changed to `\r\n`.
    - `add-eofeol`:
      Ends without a `\n`, which will be added.
    - `breakout-attempt`:
      Attempt to confuse a naïve diff parser to misinterpret a `-` or `+` content line as a `---` or `+++` declaration.
    - `changed-without-eofeol`:
      Change a line other than the last in a file that does not end with `\n`.
    - `delete-cr`:
      Contains a `\r\n` that will be changed to `\n`.
    - `delete-cr-without-eofeol`:
      Ends with a `\r` that will be deleted.
    - `delete-eofeol`:
      Ends with a `\n` that will be deleted.
    - `delete-file`:
      Content that does not appear in `../b/`.
    - `rename-file`:
      Content is preserved as file is renamed to `rename-file-2`.
    - `unchanged-file`:
      Content is unchanged.
  - `b/`:
    After change.
    - `create-file`:
      Content that does not appear in `../a/`.
    - Others:
      See comments above for `../a/*`.
  - `01-a-b.hintful.diff`:
    - Mostly a simple, minimized diff.
    - Add/remove a stray `\r`.
    - `\r` after `\` newline marker are discarded.
  - `02-a-b.invalid.hintful.diff`:
    No `\r` before `$` newline marker.
  - `03-a-b.invalid.hintful.diff`:
    No `\r` before `\` newline marker if the following content is `\n`.
  - `04-a-b.invalid.hintful.diff`:
    No `\r` before `\` newline marker if the following content is `\r\n`.
  - `05-a-b.invalid.hintful.diff`:
    One line cannot span two hunks.
- `003/`:
  Prefixed hunks, compat format, snippets.
  - `o/`:
    The original version.
    - `luhn.js`:
      Perform Luhn test validation.
    - `luhn.test.js`:
      Test `luhn.js`.
    - `package.json`:
      Minimal package description.
  - `a/`:
    Fix the original version to not validate a string with no digits.
  - `b/`:
    Fix the original version to use the Jest test framework.
  - `m/`:
    Merge versions `a` and `b`.
  - `01-o-b.hintful.diff`:
    Mix hintful and unified hunks, all unprefixed.
  - `02-o-b.invalid.compat.diff`:
    - No unprefixed hintful hunks.
    - Same file content as `01-o-b.hintful.diff`.
  - `03-o-a.compat.diff`:
    - Prefixed files in different order than unprefixed.
    - Index missing for one of the prefixed files but included for one of the prefixed files.
    - Labels missing for one of the prefixed files but included for one of the prefixed files.
  - `04-o-b.compat.diff`:
    - One hintful and one unified hunk in the same prefixed file.
    - Unprefixed file with no prefixed version.
    - More than one hunk (in the correct order) in both unprefixed and prefixed version of a file.
  - `05-a-m.compat.diff`:
    Prefixed file with one hunk missing.
  - `06-b-m.hintful.diff`:
    - Express the same content in different ways in prefixed vs unprefixed version of a hunk, both using hintful format.
    - Use same snippet in prefixed and unprefixed hunk.
  - `07-a-m.invalid.hintful.diff`:
    - Mismatch file content between prefixed and unprefixed version.
    - Based on `05-a-m.compat.diff`.
  - `08-a-m.unified.diff`:
    - Valid despite mismatched file content between prefixed and unprefixed version.
    - Same content as `07-a-m.invalid.hintful.diff`.
  - `09-b-m.invalid.hintful.diff`:
    - Mismatch snippet content between prefixed and unprefixed.
    - Based on `06-b-m.hintful.diff`.
  - `10-o-b.invalid.hintful.diff`:
    - Prefixed hunks in wrong order but unprefixed in correct order.
    - Based on `04-o-b.compat.diff`.
  - `11-o-b.invalid.hintful.diff`:
    - Unprefixed hunks in wrong order but prefixed in correct order.
    - Based on `04-o-b.compat.diff`.
  - `12-o-b.invalid.hintful.diff`:
    - Prefixed and unprefixed hunks in matching but wrong order.
    - Based on `04-o-b.compat.diff`.
  - `13-o-b.invalid.hintful.diff`:
    - A hunk with missing unprefixed version.
    - Based on `04-o-b.compat.diff`.
  - `14-o-b.invalid.hintful.diff`:
    - Prefixed file after unprefixed version.
    - Based on `04-o-b.compat.diff`.
  - `15-o-b.invalid.hintful.diff`:
    - Index mismatch between prefixed and unprefixed file.
    - Based on `04-o-b.compat.diff`.
  - `16-o-b.invalid.hintful.diff`:
    - Index present in prefixed but not unprefixed file.
    - Based on `04-o-b.compat.diff`.
  - `17-o-b.invalid.hintful.diff`:
    - Labels mismatch between prefixed and unprefixed file.
    - Based on `04-o-b.compat.diff`.
  - `18-o-b.invalid.hintful.diff`:
    - Labels present in prefixed but not unprefixed file.
    - Based on `04-o-b.compat.diff`.
  - `19-o-b.invalid.hintful.diff`:
    - Unprefixed hintful hunk after `diff --git`.
    - Based on `01-o-b.hintful.diff`.
  - `20-o-b.invalid.compat.diff`:
    - Prefixed hintful hunk after `diff --git`.
    - Based on `04-o-b.compat.diff`.
  - `21-a-m.invalid.compat.diff`:
    - Bad prefixed file header.
    - Based on `04-o-b.compat.diff`.
  - `22-a-m.invalid.compat.diff`:
    - Bad unprefixed file header.
    - Based on `04-o-b.compat.diff`.
  - `23-a-m.invalid.unified.diff`:
    - Bad unprefixed file header.
    - Same content as `22-a-m.invalid.compat.diff`.
- `004/`:
  Binary files.
  - `01-a-b.hintful.diff`:
    - Binary files handled as text.
