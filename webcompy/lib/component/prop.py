from typing import Any, Callable, Type, Dict, List
from .base import WebcompyComponentBase
from javascript import RegExp, String


repository: Dict[str, Dict[str, str]] = {}

pattern = RegExp.new(r'<function ([^\.]+).([^\>]+)>')


def prop(prop_name: str):
    def deco(method: Callable[[Type[WebcompyComponentBase], Any], None]):
        res = String.new(str(method)).match(pattern)
        if res:
            component_name, method_name = res[1:]
            if component_name not in repository:
                repository[component_name] = {}
            repository[component_name][prop_name] = method_name
        return method
    return deco


def get_observed_attributes(component_name: str) -> List[str]:
    if component_name in repository:
        prop_names = ((name, ':' + name) for name in repository[component_name].keys())
        return [name for names in prop_names for name in names]
    else:
        return list()


def get_prop_callback(component_name: str, prop_name: str):
    if component_name in repository and prop_name in repository[component_name]:
        return repository[component_name][prop_name]
    else:
        return None