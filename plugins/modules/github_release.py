#!/usr/bin/env python

from contextlib import contextmanager
from typing import Any, ContextManager

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

from ansible_collections.dstanek.software.plugins.module_utils import download
from ansible_collections.dstanek.software.plugins.module_utils import latest
from ansible_collections.dstanek.software.plugins.module_utils.common import (
    SoftwareRequest,
)
from ansible_collections.dstanek.software.plugins.module_utils.errors import (
    SoftwareException,
)

GITHUB_ARGS_DEFAULT = dict(
    download_url_template="https://{github_host}/{github_args[project]}/releases/download/{version}/{url_filename}",
    version_url_template="https://{github_host}/{github_args[project]}/releases/latest",
    host="github.com",
    # url_filename_template=None,
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
            raise Failure({"msg": "Failed to determine latest version"})

        return info["location"].split("/")[-1]

    def download(self, version) -> bytes:
        if self._module.params["github_args"]["url_filename_template"]:
            template = self._module.params["github_args"]["url_filename_template"]
            url_filename = template.format(version=version, **self._module.params)
        else:
            url_filename = self._module.params["name"]

        return download.slurp(self._module, version, url_filename=url_filename)


@contextmanager
def changed_params(
    module: AnsibleModule, key: str, value: Any
) -> ContextManager[AnsibleModule]:
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

    # for k, v in GITHUB_ARGS_DEFAULT.items():
    #     module.params["github_args"].setdefault(k, v)
    for key in ("version_url_template", "download_url_template"):
        module.params[key] = module.params[key] or GITHUB_ARGS_DEFAULT[key]

    # Let's install something
    try:
        sr = SoftwareRequest(module.params, resolver)
        changed, context = latest.run(sr, module)
    except SoftwareException as e:
        module.fail_json(e, **e.context)

    module.exit_json(changed=changed, **context)


if __name__ == "__main__":
    main()
