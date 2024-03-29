from pathlib import Path

from .errors import SoftwareException
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

        if self.state == "latest" and self.version:
            raise SoftwareException("Specify state:latest or (state:present and a specific version)")

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
    def from_param(cls, name):
        """Create a Software instance from the name parameter."""
        if "=" in name:
            return cls(*name.split("="))
        return cls(name)


def create_versioned_path(dest: str, name: str):
    dest = Path(dest)
    if dest.is_dir():
        return VersionedPath(dest / name)
    return VersionedPath(dest)
