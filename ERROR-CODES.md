# Error codes

A list of error codes, ordered and grouped according to the specification.
When a `implementations/*/validate-*-diff` script is fed an invalid diff file, it should exit with a non-zero exit code and print a message on stderr that contains one of these error codes within square brackets.
Test files `tests/*/*.invalid-*.diff` contain the expected error code in their file name and are used for test assertions.

* Hintful and unified hunk format:
  * `[HDF11]` Line counts in hunk header inconsistent with hunk content.
  * `[HDF12]` Could not parse content or snippet line.
  * `[HDF13]` Hunk ended inside snippet.
  * `[HDF15]` Snippet content does not match previous use of the same snippet name.
  * `[HDF16]` Occurrence of a `\r*\n` sequence in effective content not represented as `\r*\n`.
  * `[HDF17]` Forbidden `\ No newline at end of file`.
  * `[HDF18]` Hunk limit constraints violated.
* Hintful diff format:
  * `[HDF21]` Could not parse line that appears outside of hunk.
  * `[HDF22]` Error parsing extended headers in file comparison.
  * `[HDF23]` Hintful format hunk in unified file comparison.
  * `[HDF24]` Hunk overlaps or precedes a previous hunk.
* Prefixed file comparisons and duplicated data:
  * `[HDF31]` Prefix must be consistent throughout a file comparison.
  * `[HDF32]` Prefixed file comparison not followed by unprefixed file comparison.
  * `[HDF33]` Duplicate file comparisons can only be first a prefixed and then an unprefixed.
  * `[HDF34]` Extended header in prefixed file comparison missing in the corresponding unprefixed file comparison.
  * `[HDF35]` Extended header in prefixed file comparison does not match the corresponding unprefixed file comparison.
  * `[HDF36]` Prefixed hunk not followed by unprefixed hunk.
  * `[HDF37]` Effective content in unprefixed hunk does not match the corresponding prefixed hunk.
* Compat format:
  * `[HDF41]` Unprefixed hintful file comparison in compat diff format file.
