# Hintful diff format - Spec & Motivation

## Design goals

1. As far as possible, retain the good properties of unified diff format.
   That includes at least:
   1. Text compatible: <br/>
      If you convert both the source and patch file to another text format or encoding, the patch should still produce the correct result.
   1. Binary compatible:<br/>
      It should be possible to correctly express the difference between two binary files, even if the result isn't human readable.
   1. Usable for patching:<br/>
      It should be possible to produce the right-hand tree exactly given the diff file and the left-hand tree.
   1. Usable for reverse patching:<br/>
      It should be possible to produce the left-hand tree exactly given the diff file and the right-hand tree.
   1. Reversible:<br/>
      It should be possible to produce a diff from B to A, given a diff from A to B.
   1. Content agnostic:<br/>
      The diff format itself should work just fine no matter the syntax, or lack of syntax, of the content.
   1. Easy to implement.
   1. Be easy to mentally parse:<br/>
      In unified diff format, most of the meaning of one line can often be discerned without much context.
   1. No escaping hassle:<br/>
      Not require any escaping except at most special newline handling
1. Enable meaningfully expressed changes in any language, including for example
    1. Differences with finer granularity than one line
    1. Moving, copying and otherwise refactoring code
    1. Several independent differences that change the same line
    1. One and the same operation that affect several lines and files
    1. Any combination of the above.
1. Compatible with already existing tooling:<br/>
   It should be possible to use e.g. the *current version* of `git apply` to apply a hintful patch.

## Specification

The unified diff format has many nice properties and enjoys at least as much popularity as it deserves.
Unfortunately, it is implemented in different incompatible ways in different tools.
Bridging this gap with [one standard to rule them all](https://xkcd.com/927/) is not within the purpose or scope of this project.
Instead, this specification
* is expressed in terms of extending unified diff format.
* uses the `git` flavour of unified diff format as an example whenever talking about incompatible aspects.

### Hintful hunk format

A hintful hunk consists of a one-line hunk header followed by any number of content lines and/or snippet lines.

The hunk header has the same format as in unified diff, except the total number of lines in the hunk (excluding the header) is inserted within parenthesis between the left and right line number information.

A content line consists of
* A status marker, which is one of the following (the three first already supported by unified diff):
  * A minus (`-`) meaning the content is found only in the left file.
  * A plus (`+`) meaning the content is found only in the right file.
  * A space (` `) meaning the content is found in both the left and the right file.
  * An underscore (`_`) having the same meaning as space, except signaling that this context is less usable for human consumption.
  * A hash (`#`) meaning the content is found in neither the left nor the right file.
* Text content
* A newline marker, which is one of the following:
  * A backslash (`\`) signifying end of content.
  * A dollar sign (`$`) meaning the rest of the content line (but not the newline marker) is included in the content.
* Any number of CR characters and a newline character

A snippet line consists of
* A status marker, which is one of the following:
  * Right-angle (`>`) for using a named snippet for the right-hand side of the comparison, instead of the right file.
    Subsequent content lines is a comparison following the usual syntax, using the named snippet rather than the right file for its right-hand side, until another right-angle (`>`) marker.
  * Left-angle (`<`), conversely, for using a named snippet for the left-hand side of the comparison.
* The name of the snippet.
  As a special case, if the name is the empty string, the right or left file is again used for the right- or left-hand side of the comparison, starting where it previously left off.
* Any number of CR characters and a newline character

A hunk must not end within a snippet.

A snippet name may be used several times, but the content must match.

Any occurrence of a `\r*\n` sequence in effective content (named snippet content or left- or right-hand side file) must be represented by a `\r*\n` sequence in the hintful diff format file.

The syntax `\ No newline at end of file` as used in unified hunks is forbidden.

Similarly to unified hunks, the effective content of each side of the comparison must either end with a newline or be located at the end of a file.

### Hintful diff format

The hintful diff format is an extension of the unified diff format.
The exact meaning of "unified diff format" is unfortunately implementation dependent.

The extentions are as follows:

#### Hunk formats

A hunk may be in either hintful or unified format.
The two hunk formats may be mixed arbitrarily within a hintful diff format file.

#### Prefixed file comparisons

A "file comparison" is a section of a diff format file with a header indicating what files are compared, potentially followed by extended header information and hunks.
In hintful diff format, file comparisons can be prefixed or unprefixed.
A prefixed file comparison has a bar character (`|`) before every line.
A prefixed file comparison must have a corresponding unprefixed version of the file comparison occurring later in the hintful diff format file.
Any or all extended headers and hunks may be missing from the prefixed version of the file comparison.
Any extended headers present in the prefixed version must also be present in the unprefixed version and match exactly.
Any hunks present in the prefixed version must be correctly ordered and have a corresponding hunk in the unprefixed version.
The corresponding unprefixed hunk may be expressed with a different format or in a different way, but must have matching effective content for the left- and right-hand side of the comparison.

Tools designed to consume hintful diff format should prioritize the semantic information in the prefixed version over that in the unprefixed.

### Hintful compatibility format

The hintful compatibility diff format is a subset of the hintful diff format, with one added restriction:
No unprefixed hunks may use the hintful hunk format.

A hintful compatibility diff format file can be used as-is by tools designed to consume unified diff format.

## Motivation

### Hintful hunk header

The parenthesis and their placement are designed to cause tools that don't support hintful hunks to exit with an error if they come across an unprefixed, hintful hunk.

The hunk line count is included since it is necessary for parsing.
The line counts for old and new files are redundant information, but they are left as they are since they
* Don't have any clear downside
* Could aid human consumption
* Could potentially make it easier to extend some consuming tools.

### Status marker minus (`-`), plus (`+`) and space (` `)

These status markers are the same as in unified diff.
There is no reason to change them.

### Status marker hash (`#`)

You've already seen in the example how to use the hash (`#`) status marker.
The diff tool detected two changes; the addition of an enclosing `if` block, and the removal of an array element.
The first change produces an indent increase for every line, even for the line that in the next change is deleted.
So, while the four spaces after `#` in the diff output exists neither in the old or the new file, they do exist in an intermediate step, and are useful in visualizations for human consumption.

But this is just one possible use for it.
It can also be used to insert comments and explanations for the diff output.

I believe the hash (`#`) character is the one with the most established tradition for the meaning "human-only consumption".
While in this case it technically will be processed by visualization tools, I still think the hash character is most appropriate and will be easiest to remember.

### Status marker underscore (`_`)

Patching tools should treat the underscore just like space, while for visualization tools it's an indication that this context is less important.
Why is this necessary?
Due to the combination of three of our goals, namely text compatibility, binary compatibility and meaningfully expressed changes.
Most of the time, content that appears on the same line belong together, so showing entire lines won't hurt.
Now, since we want the format to be able to deal with content that is not line-oriented, we must be able to express changes that do not deal with an entire line.
The obvious way to do this would be to extend the hunk header to talk about both line and column counts.
This is unfortunately a bad idea, since there are so many contenders for the definition of "column".
If we want to be binary compatible, the only sensible thing is to count bytes, but then we won't be text compatible since byte count can change when translating text to a different encoding.
Counting characters is even more fraught since what constitutes a "character" depends not only on encoding, but e.g. what version of Unicode you happen to fancy.
The only way I can think of to reliably convey a column number across systems irrespective of encoding, character set and unknown binary/text status, is this:
Include the prefix text verbatim.
If the user then treats the old file and the patch as text files, the byte count will be correctly adjusted by the text encoding converter, and if the user treats them as binary it'll work just as well.
The only potential problem is excessive data shown to the user in visualization tools, which is why the underscore is introduced.
You can think of it as declaring both context and a delimiter between hunks that happen to have no newlines between them (todo clarify).

Imagine producing a diff of two minified script files, where all the code is on one line.
We don't tend to do that because our tools are lacking, but with this format it'd be quite doable.
The semantically aware diff tool could, as an intermediate step, reformat the code to its heart's content, inserting newlines and spaces to make it look nice.
Since the line containing everything was changed, the output would necessarily contain all content, but much of it could be marked with underscore so it won't bother the human.
At the point where the actual changes occur, the diff output could contain a nice mix of minus, plus, space and hash status markers to make the visualization look nice.
This will enable visualization tools with no semantical awareness to show semantically meaningful, unambiguous visualizations of diffs/patches.

The underscore (`_`) character has some established tradition for substituting space.
For this reason, I suspect it will be easiest to remember.

### Newline handling

The main feature is the backslash (`\`) or dollar sign (`$`) marker at the end of a content line.
This is what will enable diff tools to express themselves more exactly, as described above.

Its placement, at the end of the line except optionally before any CR characters, may seem a bit awkward.
It's not great, but I think it might be the least bad option.

We could have put the newline marker at the beginning of the line, either before or after the status marker, but there are several reasons not to: todo
* As far as I know, the backslash (`\`) and dollar sign (`$`) characters are the ones with the most established tradition for the meanings they are used in here.
  Adhering to tradition is good for usability, and this tradition dictates that they should be at the end.
* These markers indicate something about the newline, so putting them at the end of the line makes for more localized meaning.
* When diffing indent sensitive languages, content lines that represent only part of a code line will frequently have trailing whitespace.
  Putting the newline marker at the end clears up that visual ambiguity.
  As an added bonus, this happens even for actual trailing whitespace, which is an improvement over unified diff.
* Putting the newline marker first would break existing syntax highlighting for diff formats.
  Let's not break more things than necessary.

If we put the newline marker at the very end, we introduce a regression compared to unified diff. todo

Despite all its advantages, the newline marker does add some complexity.
It really is a kind of escaping, a newline is never represented by itself, but by a dollar sign (`$`) followed by newline.
It is certainly possible to have no escaping at all, not even for newlines.
However, such a format will not be line-based, removing the advantage for mental parsing that the meaning of each line can somewhat stand on its own.

todo
This implies that
* No CR (`\r`) character may be located immediately before a dollar sign (`$`) newline marker.
* A CR (`\r`) character may be located immediately before a backslash (`\`) newline marker only if it is not part of a `\r*\n` sequence in effective content.

todo.
The bane.
The issue with too many newline delimiter standards has a destructive force / effort of invention ratio approaching that of leap seconds.
Snippet names must not contain `\r`.
A `\r` character that is part of a `\r*\n` sequence on either side of the comparison (old file, new file, or named snippet) can be represented only as part of a `\r*\n` sequence in the diff format file.

todo
Remove requirement for `\ No newline at end of file` syntax
This syntax is merely a special case of the newline marker.
Therefore, there is no need to keep it in the proposed format.
To make implementation easy, consumers are allowed but not required to support it.
Producers must not use it.

### Named snippets
todo
Status marker right-angle (`>`) and left-angle (`<`)

These two markers are used for indicating code movement and refactoring.
These are very common operations, and having a diff format that can express them would be highly desirable.
The only thing speaking against a native notation for code movement and refactoring is the design goal of an "easy to implement" format.
Unfortunately, even though code movement syntax will complicate the format somewhat, I believe it is necessary for actual usability.

I believe the named snippet functionality strikes a good balance between simplicity and expressive power, and I hope the added complexity won't prevent adoption.
I believe a fairly simple library could be devised to convert this format to a unified diff, with access only to the patch file.

I believe the named snippet functionality fulfills all the design goals well (except of course being compatible with existing tooling).
* Similarly to unified diff, only a single pass is necessary to patch or reverse patch.
  This makes it rather simple to implement.
* Mental parsing is probably as easy as it could be.
  It's not fair to compare it to the simpler syntax of unified diff, since with that format you won't get any help at all to identify code movement or refactoring.
  It is a slightly more complicated syntax, but should be a lot more helpful in total.

Named snippets are not necessarily found as-is in either the old or new file.
Similarly to the hash (`#`) status marker, named snippets is a way to talk about an intermediate form that aids expression and understanding.
This enables several new use cases:
* It provides a generic, simple way to express both simple and complicated refactoring.
  For example, a common expression that is refactored into a function can be expressed with two named snippets, one for the function call and one for the function body.
  The function definition added to the new file can be expressed as a comparison with both snippets in sequence.
  At every location where the common expression is replaced with a function call, first the expression in the old file is compared to the function body snippet, then the function call snippet is compared to the new file.
* 3-way diff no longer requires a separate format.
  A diff in this format can use named snippets to first provide an expressive comparison between the old file and common ancestor,
  then an equally expressive comparison between the common ancestor and the new file.
  todo except git patches with file renaming takes more explanation.
  All it takes is a convention: The common ancestor consists of
  * The contents declared by the space (` `) status marker to be the same in the old and new file
  * The contents of all named snippets beginning with asterisk (`*`), at the point of their first use.
* One and the same diff format file could express a series of changes to the same code, by using a string of interlinked snippets to represent intermediate states.
  This could be used by an advanced diff tool to express several AST changes whose code happen to overlap, in a more legible way.
  Similarly, it could be used to express an entire set of patches that can then be viewed in context.
* `git diff` can already infer and output renaming of files, which is a special case of communicating a relationship between one deletion and one addition.
  Named snippets offer a way to express relationships between arbitrary changes.
  Refactoring is not limited to one file, and moving code is not limited to two files.

This design also makes sure to keep the following two properties of unified diff format:
* A beautiful symmetry that makes it trivial to produce a reverse patch from any given patch.
  Let's not destroy something so beautiful.
* The size of the new file is bounded by the sum of the old file and the patch.
  If we allowed "fast-forwarding" by ending a hunk in the middle of a named snippet, we could get exponential data growth or memory use in terms of patch size, which is undesirable.
  Technically we could allow such fast-forwarding in the case that both sides are named snippets that have been used previously and will end in a following hunk.
  However, this would complicate both the format and implementations far more than it's worth for what we'd gain.

### Hunk limits

Similarly to unified diff format, hunks must begin where the start of a line in the old file matches the start of a line in the new file, and end where a newline or end-of-file in the old file matches a newline or end-of-file in the new file.

### Mixing hunk formats

The unified and hintful hunk formats can be mixed freely within a hintful diff format file.
There are two reasons for this:
* Backwards compatibility.
* Readability.

### Prefixed file comparisons and compatibility format

The only purpose with prefixed file comparisons is for use in compatibility format.
They are designed this way to make compatibility format backwards compatible with unified diff format.

A hintful diff format file can include both prefixed file comparisons and unprefixed hintful hunks.
There might not be any reason to create such a file, but it is allowed in order to make compatibility diff format a subset of the full hintful diff format.
This way, consumers of the format will not need to distinguish between these two formats.

One might even choose to extend a consumer to read hintful format without distinguishing that from unified format.
This choice has a small price:
It would technically not be entirely backwards compatible since it is possible to violate the rules for prefixed file comparisons and thereby create an invalid hintful diff that is still a valid unified diff.
