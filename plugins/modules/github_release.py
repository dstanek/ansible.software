#!/usr/bin/env python

from contextlib import contextmanager
from typing import Any, ContextManager

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

from ansible_collections.dstanek.software.plugins.module_utils import download
from ansible_collections.dstanek.software.plugins.module_utils import latest
from ansible_collections.dstanek.software.plugins.module_utils.common import SoftwareRequest, SoftwareException

GITHUB_ARGS_DEFAULT = dict(
    download_url_template="https://{github_host}/{github_args[project]}/releases/download/{version}/{url_filename}",
    version_url_template="https://{github_host}/{github_args[project]}/releases/latest",
    host="github.com",
#    url_filename_template=None,
)

MODULE_SPEC = dict(
    name=dict(required=True, type="str"),

    dest=dict(required=True, type="path"),
    mode=dict(default=0o755, type="raw"),
    owner=dict(type="str"),
    group=dict(type="str"),

    github_args=dict(type="dict", default={}),

    release_type=dict(
        type="str",
        choices=["executable", "tarball"],
        default="executable",
    ),
    tarball_args=dict(type="dict", default={}),

    state=dict(
        type="str",
        choices=["absent", "present", "latest"],
        default="latest",
    ),
    os_platform=dict(
        type="str",
        default="linux",
    ),
    version_url_template=dict(type="str"),
    download_url_template=dict(type="str"),

    github_host=dict(type="str", default="github.com"),
)


class GithubVersionResolver:
    def __init__(self, module: AnsibleModule):
        self._module = module

    def get_latest(self) -> str:
        template = self._module.params["version_url_template"]
        url = template.format(**self._module.params)
        with changed_params(self._module, "follow_redirects", False):
            _, info = fetch_url(self._module, url, method="HEAD")
        if info["status"] not in (301, 302, 303, 307):
            raise Failure(
                {"msg": "Failed to determine latest version"}
            )
    
        return info["location"].split("/")[-1]

    def download(self, version) -> bytes:
        if self._module.params["github_args"]["url_filename_template"]:
            template = self._module.params["github_args"]["url_filename_template"]
            url_filename = template.format(version=version, **self._module.params)
        else:
            url_filename = self._module.params["name"]

        return download.slurp(self._module, version, url_filename=url_filename)


@contextmanager
def changed_params(module: AnsibleModule, key: str, value: Any) -> ContextManager[AnsibleModule]:
    undefined = object()

    old_value = module.params.get(key, undefined)
    module.params[key] = value
    try:
        yield module
    finally:
        if old_value is undefined:
            del module.params[key]
        else:
            module.params[key] = old_value


class Failure(Exception):
    def __init__(self, data):
        super().__init__()
        self.data = data


def main():
    module = AnsibleModule(argument_spec=MODULE_SPEC)
    resolver = GithubVersionResolver(module)

    #for k, v in GITHUB_ARGS_DEFAULT.items():
    #    module.params["github_args"].setdefault(k, v)
    #print(module.params)
    for key in ("version_url_template", "download_url_template"):
        module.params[key] = module.params[key] or GITHUB_ARGS_DEFAULT[key]

    # Let's install something
    sr = SoftwareRequest(module.params, resolver)
    try:
        changed, context = latest.run(sr, module)
    except SoftwareException as e:
        module.fail_json(e, **e.context)

    module.exit_json(changed=changed, **context)

    if module.params["release_version"] != "latest":
        module.fail_json(msg="Only the 'latest' release version is supported")

    #print(module.params)
    resolver = GithubVersionResolver(module)
    try:
        version = resolver.latest()
    except Failure as e:
        module.fail_json(meta=e.data)
    print("x")

    # TODO: validate this path
    dest = Path(module.params["dest"]).expanduser()
#    #if dest.is_dir():
#    #    module.params["dest"] = str(dest / module.params["name"])
#    dest = LinkedPath(module.params["dest"])
#    # TODO: should add a check here so that we don't wipe out something
#    #       we don't own, but YOLO.

    if module.params["release_type"] == "executable":
        changed, meta = download.executable(resolver, module, dest, version)
    elif module.params["release_type"] == "tarball":
        changed, meta = download.tarball(resolver, module, dest, version)
    print("y")

    module.exit_json(changed=True, meta=meta)


if __name__ == '__main__':
    main()
