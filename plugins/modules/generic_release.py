#!/usr/bin/env python3

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

from ansible_collections.dstanek.software.plugins.module_utils import absent
from ansible_collections.dstanek.software.plugins.module_utils import download
from ansible_collections.dstanek.software.plugins.module_utils import latest
from ansible_collections.dstanek.software.plugins.module_utils import present
from ansible_collections.dstanek.software.plugins.module_utils.common import (
    Software, SoftwareRequest,
)
from ansible_collections.dstanek.software.plugins.module_utils.errors import (
    SoftwareException,
)


MODULE_SPEC = dict(
    name=dict(required=True, type="str"),
    dest=dict(type="path", default="/usr/local/bin"),
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
