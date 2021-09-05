# Hintful diff format

Specification, reference implementations and test battery for Hintful diff format.

* The [MAIN.md](MAIN.md) file contains the specification, along with motivation.
* The [implementations/](implementations/) directory contains reference implementations for
  * Validating diff files in, reversing diff files in, and converting diff files from/to compatibility, hintful and unified formats.
  * Producing and consuming diff format files in unified format (by calling out to `git`).
* The [tests/](tests/) directory contains tests for the implementations in `implementations/`.
