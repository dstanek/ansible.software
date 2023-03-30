#!/usr/bin/env python3

DOCUMENTATION = r"""
---
module: dstanek.software.github_release
short_description: Download a software release from GitHub
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
      - C(files) is a list containing C({"src": ..., "dest": ...}) where C(src) is the path
        in the tarball and C(dest) is the remote path to save the file.
    default: null
    suboptions:
      files:
        type: list
        elements: dict

  github_args: {}

  state:
    type: str
    description:
      - Whether to install the latest (latest), install a specific version (present), or remove
        (absent) software.
      - `latest` will always try to get the latest version of software.
      - `present` will install a specific version if specified, or will get the latest if not
        already installed.
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
    default: "https://{github_host}/{github_args[project]}/releases/latest"

  download_url_template:
    type: str
    description:
      - A Jinja2 template for constructing the URL to download a
        specific version.
    default: "https://{github_host}/{github_args[project]}/releases/download/{version}/{url_filename}"

  github_args:
    type: dict
    options:
      github_host:
        type: str
        default: "github.com"
      github_project:
        type: str
        required: true
        default: null
      url_filename_template:
        type: str
        description:
          - A Jinja2 template to construct the filename to download
          - Defaults to C(name)
        default: null

notes: []
requirements: []
"""

EXAMPLES = r"""
- name: Install kind
  dstanek.software.github_release:
    name: kind
    dest: ~/.local/bin
    os_platform: "{{ os_platform }}"
    github_args:
      project: kubernetes-sigs/kind
      url_filename_template: "{name}-{os_platform}-amd64"

- name: Install kubectx
  dstanek.software.github_release:
    name: kubectx
    release_type: tarball
    dest: ~/.local/bin
    os_platform: "{{ os_platform }}"
    github_args:
      project: ahmetb/kubectx
      url_filename_template: "{name}_{version}_{os_platform}_x86_64.tar.gz"

- name: Install kubens
  dstanek.software.github_release:
    name: kubens
    release_type: tarball
    dest: ~/.local/bin
    os_platform: "{{ os_platform }}"
    github_args:
      project: ahmetb/kubectx
      url_filename_template: "{name}_{version}_{os_platform}_x86_64.tar.gz"
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
    release_type=dict(
        type="str",
        choices=["executable", "tarball"],
        default="executable",
    ),
    tarball_args=dict(type="dict", default={}),
    github_args=dict(type="dict", default={}),
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
