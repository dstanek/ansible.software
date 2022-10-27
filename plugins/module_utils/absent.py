from .common import Software, create_versioned_path
from .errors import SoftwareException


def run(params):
    software = Software.from_param(params.pop("name"))
    if software.version:
        raise SoftwareException(
            "version should not be specified",
            name=software.name,
            version=software.version,
        )

    dest = create_versioned_path(params.pop("dest"), software.name)
    if dest.exists():
        dest.remove()
        versioned_path = str(dest.target) if dest.target else None
        return  True, {"path": str(dest), "versioned_path": versioned_path, "state": "absent"}

    versioned_path = str(dest.target) if dest.target else None
    return  False, {"path": str(dest), "versioned_path": versioned_path, "state": "absent"}