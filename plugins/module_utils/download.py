from pathlib import Path

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.dstanek.software.plugins.module_utils import render
from ansible_collections.dstanek.software.plugins.module_utils.versioned_path import (
    VersionedPath,
)
from .errors import SoftwareException


def slurp(module: AnsibleModule, version: str, **extra_context) -> bytes:
    template = module.params["download_url_template"]
    url = template.format(version=version, **module.params, **extra_context)
    response, info = fetch_url(module, url)
    if info["status"] != 200:
        raise SoftwareException(
            f"Failed to download file: {url}",
            details=info,
        )
    return response.read()


def executable(resolver, filename: str, module, dest: Path, version: str):
    if dest.is_dir():
        dest = dest / filename
    dest = VersionedPath(dest)
    # TODO: should add a check here so that we don't wipe out something
    #       we don't own, but YOLO.

    if dest.release_version() == version and dest.target.exists():
        module.exit_json(changed=False, meta={"dest": str(dest), "version": version})

    file_args = module.load_file_common_arguments(module.params)

    data = resolver.download(version)
    dest.write_target(data, version, file_args)
    dest.relink(version)
    return True, {"dest": str(dest), "version": version}


def tarball(resolver, module: AnsibleModule, dest_dir: Path, version: str):

    # TODO: valudate that dest_dir is only a directory

    import io
    import tarfile

    p = module.params

    file_specs = p["tarball_args"].get("files")
    if not file_specs:
        file_specs = [{"src": p["name"], "dest": p["name"]}]

    versioned_paths = [
        VersionedPath(dest_dir / file_spec["dest"]) for file_spec in file_specs
    ]

    # If all links are correct then don't do anything
    if all(
        vp.release_version() == version and vp.target.exists() for vp in versioned_paths
    ):
        module.exit_json(
            changed=False, meta={"dest": str(dest_dir), "version": version}
        )

    data = resolver.download(version)
    tarball_data = io.BytesIO(data)
    tf = tarfile.open(fileobj=tarball_data, mode="r:gz")
    #print(tf.getnames())

    file_args = module.load_file_common_arguments(module.params)
    for file_spec in file_specs:
        dest = VersionedPath(dest_dir / file_spec["dest"])

        # New style substitution
        filename = render.string(file_spec["src"], **module.params, version=version)

        # TODO deprecate old style substitution
        filename = file_spec["src"].format(**module.params)

        member = tf.getmember(filename)
        filedata = tf.extractfile(member)
        dest.write_target(filedata.read(), version, file_args)
        dest.relink(version)
    return True, {"dest": str(dest), "version": version}
