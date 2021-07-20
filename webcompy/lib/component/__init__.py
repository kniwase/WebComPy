from .base import WebcompyComponentBase, WebcompyComponent
from .decorator import define_component
from .register import register_webcomponent
from .prop import prop

__all__ = [
    'WebcompyComponentBase',
    'WebcompyComponent',
    'define_component',
    'register_webcomponent',
    'get_observed_attributes',
    'get_component_tag_name',
    'prop',
]
