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
   1. Compatible with already existing tooling:<br/>
      It should be possible to use e.g. the current `git` Without rewriting or updating e.g. `git`,
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

Tools designed to consume hintful diff format should prioritize the semantic information in the prefixed version of that in the unprefixed.

### Hintful compatibility format

The hintful compatibility diff format is a subset of the hintful diff format, with one added restriction:
No unprefixed hunks may use the hintful hunk format.

A hintful compatibility diff format file can be used as-is by tools designed to consume unified diff format.

## Motivation

### Hunk header
### Status markers
### Newline handling

This implies that
* No CR (`\r`) character may be located immediately before a dollar sign (`$`) newline marker.
* A CR (`\r`) character may be located immediately before a backslash (`\`) newline marker only if it is not part of a `\r*\n` sequence in effective content.

todo.
The bane.
The issue with too many newline delimiter standards has a destructive force / effort of invention ratio approaching that of leap seconds.
Snippet names must not contain `\r`.
A `\r` character that is part of a `\r*\n` sequence on either side of the comparison (old file, new file, or named snippet) can be represented only as part of a `\r*\n` sequence in the diff format file.

### Named snippets
### Hunk limits
### Mixing hunk formats
### Prefixed file comparisons
### Compatibility format

## Roadmap

### Step 1: Reach beta quality

**This is where we are currently**

Critique hintful diff format as soon as possible so that it doesn't get finalized with an inherent problem.
If you suspect a potential problem, open an issue even if you're not sure or don't have a solution.

### Step 2: Tool implementation trial and finalization

After the beta is released, implement the format in your project in a non-production branch/release.
We'd like a couple of different producers and consumers to try it out and reveal as many remaining problems as possible.
This experience is used to finalize the format.

### Step 3: Tool implementation

After the format is finalized, implement it in your project and feel free to release it.

For producers such as `diff`, `git diff` and semantic diff tools you could for example
* Add two CLI flags, one for hintful format and one for hintful compatibility format, **or**
* Change your tool to produce hintful compatibility format by default, with a flag to switch to hintful format.

For consumers such as `patch`, `git apply` and diff visualizers, you could for example
* Extend your tool to accept hintful format since it is (almost) a superset of unified diff format, **or**
* Add a CLI flag to accept hintful format.
