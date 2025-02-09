import re

from semver import Version

_re_partial_version = re.compile(r"^([0-9]+)(?:\.([0-9]+)(?:\.([0-9]+))?)?$")


def _parse_partial_version(x):
    m = _re_partial_version.match(x)
    if m is None:
        return None, None
    major, minor, patch = m.groups()
    v = Version(major, minor or 0, patch or 0)
    n = 1 if minor is None else 2 if patch is None else 3
    return (v, n)


class Compat:
    """A Julia compat specifier."""

    def __init__(self, clauses=[]):
        self.clauses = [clause for clause in clauses if not clause.is_empty()]

    def __str__(self):
        return ", ".join(str(clause) for clause in self.clauses)

    def __repr__(self):
        return f"{type(self).__name__}({self.clauses!r})"

    def __contains__(self, v):
        return any(v in clause for clause in self.clauses)

    def __and__(self, other):
        clauses = []
        for clause1 in self.clauses:
            for clause2 in other.clauses:
                clause = clause1 & clause2
                if not clause.is_empty():
                    clauses.append(clause)
        return Compat(clauses)

    def __bool__(self):
        return bool(self.clauses)

    def __eq__(self, other):
        return self.clauses == other.clauses

    @classmethod
    def parse(cls, verstr):
        """Parse a Julia compat specifier from a string.

        A specifier is a comma-separated list of clauses. The prefixes '^', '~' and '='
        are supported. No prefix is equivalent to '^'.
        """
        clauses = []
        if verstr.strip():
            for part in verstr.split(","):
                clause = Range.parse(part)
                clauses.append(clause)
        return cls(clauses)


class Range:
    def __init__(self, lo, hi):
        self.lo = lo
        self.hi = hi

    @classmethod
    def tilde(cls, v, n):
        lo = Version(
            v.major,
            v.minor if n >= 2 else 0,
            v.patch if n >= 3 else 0,
        )
        hi = (
            v.bump_major()
            if n < 2
            else v.bump_minor()
            if v.major != 0 or v.minor != 0 or n < 3
            else v.bump_patch()
        )
        return Range(lo, hi)

    @classmethod
    def caret(cls, v, n):
        lo = Version(
            v.major,
            v.minor if n >= 2 else 0,
            v.patch if n >= 3 else 0,
        )
        hi = (
            v.bump_major()
            if v.major != 0 or n < 2
            else v.bump_minor()
            if v.minor != 0 or n < 3
            else v.bump_patch()
        )
        return Range(lo, hi)

    @classmethod
    def equality(cls, v):
        lo = v
        hi = v.bump_patch()
        return Range(lo, hi)

    @classmethod
    def hyphen(cls, v1, v2, n):
        lo = v1
        hi = v2.bump_major() if n < 2 else v2.bump_minor() if n < 3 else v2.bump_patch()
        return Range(lo, hi)

    @classmethod
    def parse(cls, x):
        x = x.strip()
        if x.startswith("~"):
            # tilde specifier
            v, n = _parse_partial_version(x[1:])
            if v is not None:
                return cls.tilde(v, n)
        elif x.startswith("="):
            # equality specifier
            v, n = _parse_partial_version(x[1:])
            if v is not None and n == 3:
                return cls.equality(v)
        elif " - " in x:
            # range specifier
            part1, part2 = x.split(" - ", 1)
            v1, _ = _parse_partial_version(part1.strip())
            v2, n = _parse_partial_version(part2.strip())
            if v1 is not None and v2 is not None:
                return cls.hyphen(v1, v2, n)
        else:
            # caret specifier
            v, n = _parse_partial_version(x[1:] if x.startswith("^") else x)
            if v is not None:
                return cls.caret(v, n)
        raise ValueError(f"invalid version specifier: {x}")

    def __str__(self):
        lo = self.lo
        hi = self.hi
        if self == Range.equality(lo):
            return f"={lo.major}.{lo.minor}.{lo.patch}"
        if self == Range.caret(lo, 1):
            return f"^{lo.major}"
        if self == Range.caret(lo, 2):
            return f"^{lo.major}.{lo.minor}"
        if self == Range.caret(lo, 3):
            return f"^{lo.major}.{lo.minor}.{lo.patch}"
        if self == Range.tilde(lo, 1):
            return f"~{lo.major}"
        if self == Range.tilde(lo, 2):
            return f"~{lo.major}.{lo.minor}"
        if self == Range.tilde(lo, 3):
            return f"~{lo.major}.{lo.minor}.{lo.patch}"
        lostr = f"{lo.major}.{lo.minor}.{lo.patch}"
        if hi.major > 0 and hi.minor == 0 and hi.patch == 0:
            return f"{lostr} - {hi.major - 1}"
        if hi.minor > 0 and hi.patch == 0:
            return f"{lostr} - {hi.major}.{hi.minor - 1}"
        if hi.patch > 0:
            return f"{lostr} - {hi.major}.{hi.minor}.{hi.patch - 1}"
        raise ValueError("invalid range")

    def __repr__(self):
        return f"{type(self).__name__}({self.lo!r}, {self.hi!r})"

    def __contains__(self, v):
        return self.lo <= v < self.hi

    def __and__(self, other):
        lo = max(self.lo, other.lo)
        hi = min(self.hi, other.hi)
        return Range(lo, hi)

    def __eq__(self, other):
        return (self.lo == other.lo and self.hi == other.hi) or (
            self.is_empty() and other.is_empty()
        )

    def is_empty(self):
        return not (self.lo < self.hi)
