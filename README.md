# Hintful diff format

Specification, reference implementations and test battery for Hintful diff format.

* The [MAIN.md](MAIN.md) file contains the specification, along with motivation.
* The [implementations/](implementations/) directory contains reference implementations for
  * Validating diff files in, reversing diff files in, and converting diff files from/to compatibility, hintful and unified formats.
  * Producing and consuming diff format files in unified format (by calling out to `git`).
* The [tests/](tests/) directory contains tests for the implementations in `implementations/`.

# How to help

You can help by opening and discussing issues about
  * Inconsistencies, bugs, unclear or incomplete documentation
  * Potential problems or weaknesses, even if you don't have a better idea
  * Discussions about the advantages and drawbacks of any of the design choices.
    The [specification](MAIN.md) should include a summary of them in the `Motivation` section.

# Roadmap and how to help

## Step 1: Reach beta quality

**This is where we are currently**

Critique hintful diff format as soon as possible so that it doesn't get finalized with an inherent problem.
If you suspect a potential problem, open an issue even if you're not sure or don't have a solution.

## Step 2: Tool implementation trial and finalization

After the beta is released, implement the format in your project in a non-production branch/release.
We'd like a couple of different producers and consumers to try it out and reveal as many remaining problems as possible.
This experience is used to finalize the format.

## Step 3: Tool implementation

After the format is finalized, implement it in your project and feel free to release it.

For producers such as `diff`, `git diff` and semantic diff tools you could for example
  * Add two CLI flags, one for hintful format and one for hintful compatibility format, **or**
  * Switch to producing hintful compatibility format by default, with a flag to switch to hintful format.

For consumers such as `patch`, `git apply` and diff visualizers, you could for example
* Extend your tool to accept hintful format since it is (almost) a superset of unified diff format, **or**
* Add a CLI flag to accept hintful format.

A plausible road to widespread adoption looks something like this:
* Tools with an inherent need for features of hintful diff format, such as semantic diff and visualization tooling, implement the format immediately.
  Producers will probably use compatibility format by default.
* After some years of establishing and validating the usefulness of the format, a few communities will hopefully begin a push to switch to hintful format that is not compatible with unified diff format.
  This push will probably be fuelled by the prospect of smaller diff/patch files that is nicer to read, and enabled by the possibility of using a small tools to convert to unified diff format to interact with legacy tooling.
* After some years of an increasing number of communities using hintful diff format in this way, legacy tooling with no inherent need for the features of hintful diff format (such as git), implement it due to popular demand ("No more aliasing `git apply-hintful`, and the new `git diff --word-diff --hintful` produces viable patches!").
* After legacy tooling supports hintful diff format, new tools with no history to be backwards compatibility with, can plausibly implement only hintful diff format.
  (For consumers, this includes compatibility format.)
