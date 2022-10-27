from pathlib import Path

from .errors import SoftwareException
from . import download


def run(sr, module):
    # TODO: validate this path
    dest = Path(module.params["dest"]).expanduser()
    if not dest.is_dir():
        raise SoftwareException("dest must be a directory")

    if module.params["release_type"] == "executable":
        changed, meta = download.executable(
            sr.resolver, sr.name, module, dest, sr.version
        )
    elif module.params["release_type"] == "tarball":
        changed, meta = download.tarball(sr.resolver, module, dest, sr.version)

    return changed, meta
