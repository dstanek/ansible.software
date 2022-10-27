from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible_collections.dstanek.software.plugins.module_utils.versioned_path import Path, VersionedPath
from .errors import SoftwareException


def slurp(module: AnsibleModule, version: str, **extra_context) -> bytes:
    template = module.params["download_url_template"]
    url = template.format(version=version, **module.params, **extra_context)
    response, info = fetch_url(module, url)
    if info["status"] != 200:
        raise Exception(
            {"msg": f"Failed to download executable: {url}"}
        )
    return response.read()


def executable(resolver, filename: str, module, dest: Path, version: str):
    if dest.is_dir():
        dest = dest / filename
    dest = VersionedPath(dest)
    # TODO: should add a check here so that we don't wipe out something
    #       we don't own, but YOLO.

    print("X", dest.release_version(), version)
    if dest.release_version() == version:
        module.exit_json(changed=False, meta={"dest": str(dest), "version": version})

    data = resolver.download(version)
    dest.write_target(data, version)

    file_args = module.load_file_common_arguments(module.params)
    dest.ensure_file_attrs(file_args["mode"], file_args["owner"], file_args["group"])
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
    if all(vp.release_version() == version for vp in versioned_paths):
        module.exit_json(changed=False, meta={"dest": str(dest_dir), "version": version})

    data = resolver.download(version)
    tarball_data = io.BytesIO(data)
    tf = tarfile.open(fileobj=tarball_data, mode="r:gz")

    file_args = module.load_file_common_arguments(module.params)
    for file_spec in file_specs:
        dest = VersionedPath(dest_dir / file_spec["dest"])
        member = tf.getmember(file_spec["src"])
        filedata = tf.extractfile(member)
        dest.write_target(filedata.read(), version)
        dest.ensure_file_attrs(file_args["mode"], file_args["owner"], file_args["group"])
        dest.relink(version)
    return True, {"dest": str(dest), "version": version}
