from typing import Dict, Optional

from .errors import SoftwareException

class EmptyPath:
    def __bool__(self):
        return False

    def exists(self):
        return False

    def unlink(self):
        return None


class VersionedPath:
    def __init__(self, path) -> None:
        self.path = path
        if self.path.is_symlink():
            self.target = self.path.resolve()
        elif self.path.exists():
            raise SoftwareException(
                "Path exists; manual intervention required", path=str(path)
            )
        else:
            self.target = EmptyPath()

    def __str__(self):
        return str(self.path)

    def relink(self, version: str, delete_old_target=True):
        new_target = self.path.parent / f"{self.path.stem}-{version}"
        if self.target and self.target != new_target and delete_old_target:
            self.target.resolve().unlink()

        self.path.unlink(missing_ok=True)
        self.path.symlink_to(new_target)
        self.target = new_target

    def release_version(self):
        if not self.target:
            return None
        return str(self.target)[len(str(self.path)) + 1 :]

    def write_target(self, data: bytes, version, file_args: Dict[str, Optional[str]]):
        new_target = self.path.parent / f"{self.path.stem}-{version}"
        new_target.write_bytes(data)
        if file_args["mode"]:
            new_target.chmod(file_args["mode"])
        if file_args["owner"]:
            new_target.owner(file_args["owner"])
        if file_args["group"]:
            new_target.group(file_args["group"])

    def remove(self):
        if self.target.exists():
            self.target.unlink()
        if self.path.exists() or self.path.is_symlink():
            self.path.unlink(missing_ok=True)

    def exists(self):
        return self.path.exists() or (self.target and self.target.exists())

    def verify(self, expected_version: Optional[str]):
        if expected_version and self.release_version() != expected_version:
            return False
        return self.path.exists() and self.target.exists()
