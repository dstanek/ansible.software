from pathlib import Path

from .versioned_path import VersionedPath
from .errors import SoftwareException
from . import download


def run(sr, module, software, resolver):
    dest = Path(module.params["dest"]).expanduser()
    if not dest.is_dir():
        raise SoftwareException("dest must be a directory", path=dest)

    vpath = VersionedPath(dest / software.name)
    if vpath.verify(software.version):
        module.exit_json(
            changed=False, meta={"dest": str(dest), "version": software.version}
        )

    if module.params["release_type"] == "executable":
        changed, meta = download.executable(
            sr.resolver, sr.name, module, dest, sr.version
        )
    elif module.params["release_type"] == "tarball":
        changed, meta = download.tarball(sr.resolver, module, dest, sr.version)

    return changed, meta
