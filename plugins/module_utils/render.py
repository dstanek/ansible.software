from typing import Dict

from ansible.module_utils.basic import AnsibleModule
import jinja2

def string(s: str, **kwargs: Dict[str, str]):
    return jinja2.Template(s).render(**kwargs)
