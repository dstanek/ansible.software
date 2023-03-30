#!/usr/bin/env python3

DOCUMENTATION = r"""
---
module: dstanek.software.generic_release
short_description: Download a software release
description:
  - "TODO: add some details"
author: "David Stanek (@dstanek)"
options:
  name:
    type: str
    description:
      - Executable name or executable name with version.
      - Used to find the software to download and as the name of the file on disk.
      - Can either be just a name like 'foo' or it can contain a version like 'foo==1.0.0'.
    required: true
    default: null

  dest:
    type: path
    description:
      - Remote absolute path where the file should be copied to.
    default: "/usr/local/bin"

  mode:
    type: raw
    description:
      - The permissions of the destination file.
      - For those used to C(/usr/bin/chmod) remember that modes are actually octal numbers.
        You must either add a leading zero so that Ansible's YAML parser knows it is an octal
        number (like C(0644) or C(01777)) or quote it (like C('644') or C('1777')) so Ansible
        receives a string and can do its own conversion from string into number. Giving Ansible
        a number without following one of these rules will end up with a decimal number which
        will have unexpected results.
      - As of Ansible 1.8, the mode may be specified as a symbolic mode (for example, C(u+rwx)
        or C(u=rw,g=r,o=r)).
    default: "755"

  owner:
    type: str
    description:
      - Name of the user that should own the destination file, as would be fed to chown.
    required: true
    default: null

  group:
    type: str
    description:
      - Name of the group that should own the destination file, as would be fed to chown.
    default: null

  release_type:
    type: str
    description:
      - Specifies if the release is an executable or packaged in a tarball.
    default: executable
    choices:
      - executable
      - tarball

  tarball_args:
    type: dict
    description:
      - Options for dealing with a tarball release.
      - C(files) is a list containing a dictionary where C(src) is the path
        in the tarball and C(dest) is the remote path to save the file.
    default: null
    suboptions:
      files:
        type: list
        elements: dict

  state:
    type: str
    description:
      - Whether to install the latest (latest), install a specific version (present), or remove
        (absent) software.
      - "`latest` will always try to get the latest version of software."
      - "`present` will install a specific version if specified, or will get the latest if not
        already installed."
    default: latest
    choices:
      - latest
      - present
      - absent

  os_platform:
    type: str
    description:
      - Currently only used for substitution.
    default: linux
    removed_in_version: 0.6.0

  version_url_template:
    type: str
    description:
      - A Jinja2 template for constructing the URL to check for
        the current version.
    required: true
    default: null

  download_url_template:
    type: str
    description:
      - A Jinja2 template for constructing the URL to download a
        specific version.
    required: true
    default: null

notes: []
requirements: []
"""

EXAMPLES = r"""
- name: Install kubectl with hardcoded platform
  dstanek.software.generic_release:
    name: kubectl
    dest: ~/.local/bin
    version_url_template: https://dl.k8s.io/release/stable.txt
    download_url_template: https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl

- name: Install kubectl with variable platform
  dstanek.software.generic_release:
    name: kubectl
    dest: ~/.local/bin
    os_platform: "darwin"
    version_url_template: https://dl.k8s.io/release/stable.txt
    download_url_template: https://dl.k8s.io/release/{version}/bin/{os_platform}/amd64/kubectl
"""

RETURN = r"""
dest:
  description: Path of saved executable
  type: path
  returned: always
  sample: /usr/local/bin/kubectl
version:
  description: Installed version
  type: str
  returned: always
  sample: 0.5.4
"""

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
        removed_in_version="0.6.0",
    ),
    version_url_template=dict(type="str"),
    download_url_template=dict(type="str", required=True),
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
