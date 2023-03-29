#!/usr/bin/env python3

from contextlib import contextmanager
from typing import Any, ContextManager

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

from ansible_collections.dstanek.software.plugins.module_utils import absent
from ansible_collections.dstanek.software.plugins.module_utils import download
from ansible_collections.dstanek.software.plugins.module_utils import latest
from ansible_collections.dstanek.software.plugins.module_utils import present
from ansible_collections.dstanek.software.plugins.module_utils import render
from ansible_collections.dstanek.software.plugins.module_utils.common import (
    Software, SoftwareRequest,
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
    dest=dict(type="path", default="/usr/local/bin"),
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
    github_project=dict(type="str")
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
            raise SoftwareException("Failed to determine latest version")

        return info["location"].split("/")[-1]

    def download(self, version) -> bytes:
        if "url_filename_template" in self._module.params["github_args"]:
            url_filename = self._module.params["github_args"]["url_filename_template"]
        else:
            # Works for both package and package=1.0
            url_filename = self._module.params["name"].split("=")[0]

        # New style substitution
        url_filename = render.string(url_filename, version=version, **self._module.params)

        # TODO deprecate old style substitution
        url_filename = url_filename.format(version=version, **self._module.params)

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


def main():
    module = AnsibleModule(argument_spec=MODULE_SPEC)
    resolver = GithubVersionResolver(module)

    for key in ("version_url_template", "download_url_template"):
        module.params[key] = module.params[key] or GITHUB_ARGS_DEFAULT[key]

    try:
        # Maybe we want to uninstall something?
        if module.params["state"] == "absent":
            changed, context = absent.run(module.params)

        # Maybe we just want to see if *any* version is installed
        elif module.params["state"] == "present":
            sr = SoftwareRequest(module.params, resolver)
            software = Software.from_param(module.params["name"])
            changed, context = present.run(sr, module, software, resolver)

        # Let's install the latest version
        elif module.params["state"] == "latest":
            sr = SoftwareRequest(module.params, resolver)
            changed, context = latest.run(sr, module)

        else:
            raise Exception("what here?")  # TODO: do something here...

        module.exit_json(changed=changed, **context)

    except SoftwareException as e:
        module.fail_json(str(e), **e.context)
    except PermissionError as e:
        module.fail_json(
            e.strerror,
            errno=e.errno,
            path=e.filename,
        )

    module.exit_json(changed=changed, **context)


if __name__ == "__main__":
    main()
