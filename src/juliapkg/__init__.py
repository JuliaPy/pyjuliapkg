from .deps import (
                   PkgSpec,
                   add,
                   executable,
                   offline,
                   project,
                   require_julia,
                   resolve,
                   rm,
                   status,
)

__all__ = [
    "status",
    "resolve",
    "executable",
    "project",
    "PkgSpec",
    "require_julia",
    "add",
    "rm",
    "offline",
]
