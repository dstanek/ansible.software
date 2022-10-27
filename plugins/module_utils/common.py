from pathlib import Path

from .versioned_path import VersionedPath

class AttrDict(dict):
    __getattr__ = dict.__getitem__


class SoftwareRequest:
    def __init__(self, params, resolver):
        params = AttrDict(params)
        self.state = params.state

        if "=" in params.name:
            self.name, self.version = params.name.split("=")
        else:
            self.name = params.name
            self.version = None

        if self.state == "latest" or (self.state == "present" and not self.version):
            self.version = resolver.get_latest()

        self.dest = params.dest
        self.extra_params = params
        self.resolver = resolver


class Software:
    def __init__(self, name, version=None):
        self.name = name
        self.version = version

    @classmethod
    def from_param(cls, value):
        """Create a Software instance from the name parameter."""
        if "=" in value:
            return cls(*value.split("="))
        return cls(value)


def create_versioned_path(dest: str, name: str):
    print("dest =", dest, "  name =", name)
    dest = Path(dest)
    if dest.is_dir():
        return VersionedPath(dest / name)
    return VersionedPath(dest)
