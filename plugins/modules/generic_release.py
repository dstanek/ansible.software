#!/usr/bin/env python

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

from ansible_collections.dstanek.software.plugins.module_utils import absent
from ansible_collections.dstanek.software.plugins.module_utils import download
from ansible_collections.dstanek.software.plugins.module_utils import latest
from ansible_collections.dstanek.software.plugins.module_utils.common import SoftwareRequest, SoftwareException


MODULE_SPEC = dict(
    name=dict(required=True, type="str"),

    dest=dict(required=True, type="path"),
    mode=dict(default=0o755, type="raw"),
    owner=dict(type="str"),
    group=dict(type="str"),

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
)


class GenericResolver:
    def __init__(self, module: AnsibleModule):
        self._module = module

    def get_latest(self) -> str:
        template = self._module.params["version_url_template"]
        url = template.format(**self._module.params)
        response, _ = fetch_url(self._module, url)
        return response.read().decode("utf8")

    def download(self, version) -> bytes:
        return download.slurp(self._module, version)


def main():
    module = AnsibleModule(argument_spec=MODULE_SPEC)
    resolver = GenericResolver(module)

    # Maybe we want to uninstall something?
    if module.params["state"] == "absent":
        try:
            changed, context = absent.run(module.params)
        except SoftwareException as e:
            module.fail_json(e, **e.context)

        module.exit_json(changed=changed, **context)

    # Let's install something
    sr = SoftwareRequest(module.params, resolver)
    try:
        changed, context = latest.run(sr, module)
    except SoftwareException as e:
        module.fail_json(e, **e.context)

    module.exit_json(changed=changed, **context)


if __name__ == '__main__':
    main()
