import re
import semantic_version as sv


Version = sv.Version


class Compat:
    """A Julia compat specifier."""

    re_range = re.compile(r'^([~^])?([0-9]+)(?:\.([0-9]+)(?:\.([0-9]+))?)?$')

    def __init__(self, clauses=[]):
        self.clauses = list(clauses)

    def __str__(self):
        return ', '.join(str(clause) for clause in self.clauses)

    def __repr__(self):
        return f'{type(self).__name__}({self.clauses!r})'

    def __contains__(self, v):
        return any(v in clause for clause in self.clauses)

    def __and__(self, other):
        clauses = []
        for clause1 in self.clauses:
            for clause2 in other.clauses:
                clause = clause1 & clause2
                if clause is not None:
                    clauses.append(clause)
        return Compat(clauses)

    def __bool__(self):
        return bool(self.clauses)

    @classmethod
    def parse(cls, verstr):
        """Parse a Julia compat specifier from a string.

        A specifier is a comma-separated list of clauses. The prefixes '^', '~' and '=='
        are supported. No prefix is equivalent to '^'.
        """
        clauses = []
        if verstr.strip():
            for part in verstr.split(','):
                part = part.strip()
                m = cls.re_range.match(part)
                if m is not None:
                    prefix, major, minor, patch = m.groups()
                    prefix = prefix or '^'
                    assert prefix in ('^', '~')
                    major = int(major)
                    minor = None if minor is None else int(minor)
                    patch = None if patch is None else int(patch)
                    version = Version(major=major, minor=minor or 0, patch=patch or 0)
                    if prefix == '^':
                        if major != 0 or minor is None:
                            nfixed = 1
                        elif minor != 0 or patch is None:
                            nfixed = 2
                        else:
                            nfixed = 3
                    elif prefix == '~':
                        if minor is None:
                            nfixed = 1
                        else:
                            nfixed = 2
                    clause = Range(version, nfixed)
                elif part.startswith('=='):
                    version = Version(part[2:])
                    clause = Eq(version)
                else:
                    raise ValueError(f'invalid version: {part!r}')
                clauses.append(clause)
        return cls(clauses)


class Eq:

    def __init__(self, version):
        self.version = version

    def __str__(self):
        return f'=={self.version}'

    def __repr__(self):
        return f'{type(self).__name__}({self.version!r})'

    def __contains__(self, v):
        if isinstance(v, Version):
            return v == self.version
        return False

    def __and__(self, other):
        if self.version in other:
            return self


class Range:

    def __init__(self, version, nfixed):
        self.version = version
        self.nfixed = nfixed

    def __str__(self):
        v = self.version
        n = self.nfixed
        if n == 1:
            if v.major != 0:
                if v.patch != 0:
                    return f'^{v.major}.{v.minor}.{v.patch}'
                elif v.minor != 0:
                    return f'^{v.major}.{v.minor}'
                else:
                    return f'^{v.major}'
            elif v.minor == 0 and v.patch == 0:
                return f'^0'
            else:
                assert False
        elif n == 2:
            if v.major == 0:
                if v.minor == 0:
                    if v.patch == 0:
                        return f'~0.0'
                    else:
                        return f'~0.0.{v.patch}'
                else:
                    if v.patch == 0:
                        return f'^0.{v.minor}'
                    else:
                        return f'^0.{v.minor}.{v.patch}'
            else:
                if v.patch == 0:
                    return f'~{v.major}.{v.minor}'
                else:
                    return f'~{v.major}.{v.minor}.{v.patch}'
        elif n == 3:
            if v.major == 0 and v.minor == 0:
                return f'^0.0.{v.patch}'
            else:
                assert False
        else:
            assert False

    def __repr__(self):
        return f'{type(self).__name__}({self.version!r}, {self.nfixed!r})'

    def __contains__(self, v):
        if isinstance(v, Version):
            n = self.nfixed
            v0 = self.version
            return (n < 1 or v.major == v0.major) and (n < 2 or v.minor == v0.minor) and (n < 3 or v.patch == v0.patch) and v >= v0

    def __and__(self, other):
        if isinstance(other, Range):
            n0 = self.nfixed
            v0 = self.version
            n1 = other.nfixed
            v1 = other.version
            nmin = min(n0, n1)
            nmax = max(n0, n1)
            vmax = max(v0, v1)
            if (nmin < 1 or v0.major == v1.major) and (nmin < 2 or v0.minor == v1.minor) and (nmin < 3 or v0.patch == v1.patch):
                if vmax in self and vmax in other:
                    return Range(vmax, nmax)
        elif isinstance(other, Eq):
            if other.version in self:
                return other
        else:
            return NotImplemented
