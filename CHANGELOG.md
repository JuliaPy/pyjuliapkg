# Changelog

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
