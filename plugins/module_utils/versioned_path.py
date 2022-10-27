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
            self.target = self.path.readlink()
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
        return str(self.target)[len(str(self.path))+1:]
        raise Exception(f"{self.target} {self.path}")
        try:
            return str(self.target).rsplit("-", 1)[-1]
        except OSError:
            """This is not a symlink"""
        except AttributeError:
            """The symlink isn't a versioned file"""

    def ensure_file_attrs(self, mode: str = None, owner: str = None, group: str = None) -> None:
        if mode:
            self.target.chmod(mode)
        if owner:
            self.target.owner(owner)
        if group:
            self.target.group(group)

    def write_target(self, data: bytes, version):
        if not self.target:
            self.target = self.path.parent / f"{self.path.stem}-{version}"
        self.target.write_bytes(data)

    def remove(self):
        if self.target.exists():
            self.target.unlink()
        if self.path.exists():
            self.path.unlink(missing_ok=True)

    def exists(self):
        return self.path.exists() or (self.target and self.target.exists())
