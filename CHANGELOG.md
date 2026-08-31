# Changelog

## Unreleased
* Julia's bundled OpenSSL is given private library names after installation, and its
  stdlib `OpenSSL_jll` is pointed at those names, so a libcrypto already loaded by CPython
  can no longer be substituted for it. Python's OpenSSL version therefore no longer
  restricts which Julia may be used, and the `<=python` bound on `OpenSSL_jll` is dropped
  from Julia 1.12 on, where it is a stdlib and cannot be pinned by Pkg. Only installations
  juliapkg created are renamed. Where the Julia that would collide was found on the system,
  one is installed and renamed instead; where even that is not possible, the previous
  restriction to Julia <1.12 still applies. Projects resolved by an earlier version resolve
  once more, so that their installed Julia is renamed too.

## v0.1.26 (2026-08-14)
* Add `julia_args` argument to `resolve()`.

## v0.1.25 (2026-08-07)
* Add preferences support.

## v0.1.24 (2026-05-31)
* Add `libjulia()` function.

## v0.1.23 (2026-02-16)
* Compat fix for juliaup 1.19.8.

## v0.1.22 (2025-10-08)
* Bug fixes.

## v0.1.21 (2025-10-08)
* Improve OpenSSL compatibility - if Python has OpenSSL <3.5, restrict to Julia <1.12.

## v0.1.20 (2025-09-19)
* The UUID is no longer required when adding a dependency.
* If the project is explicitly specified, it is considered "shared" and existing
  dependencies are never removed.

## v0.1.19 (2025-09-17)
* Add the CLI.
* Improve some error messages.

## v0.1.18 (2025-09-01)
* Support editable dependencies from setuptools (experimental).
* Add `update()` function.
* Improved input validation.
* Require Python 3.9+.

## v0.1.17 (2025-05-13)
* Respect `JULIAUP_DEPOT_PATH` when searching for Julia using juliaup.
* Add special handling of `<=python` version for OpenSSL compatibility between Julia and Python.
* Bug fixes.

## v0.1.16 (2025-02-18)
* Adds file-locking to protect multiple concurrent resolves.

## v0.1.15 (2024-11-08)
* Bug fixes.

## v0.1.14 (2024-10-20)
* When testing if a file has changed, now checks the actual content in addition to the
  modification time.

## v0.1.13 (2024-05-12)
* Internal changes.

## v0.1.12 (2024-05-12)
* Hyphen compat bounds (e.g. "1.6 - 1") now supported.
* Resolving no longer throws an error from nested environments.
* Bug fixes.

## v0.1.11 (2024-03-15)
* Moved repo to [JuliaPy github org](https://github.com/JuliaPy).
* Julia registry is now always updated when resolving.
