from webcompy.router import Router

from .pages.async_nav import AsyncNavPage
from .pages.bundled_deps import BundledDepsPage
from .pages.classstyle import ClassStylePage
from .pages.client_only import ClientOnlyPage
from .pages.component import FunctionStylePage
from .pages.custom_element import CustomElementPage
from .pages.di_test import DiInjectPage, DiProviderWrapper
from .pages.dict_repeat import DictRepeatPage
from .pages.error_handling import CatchEventsPage, ErrorBoundaryPage, NestedCrashPage
from .pages.event import EventPage
from .pages.form_fields import FormFieldsPage
from .pages.home import HomePage
from .pages.html_parser_parity import HtmlParserParityPage
from .pages.keyed_repeat import KeyedRepeatPage
from .pages.lifecycle import LifecyclePage
from .pages.markdown_for import MarkdownForPage
from .pages.nested_docs import (
    NestedDocsApiPage,
    NestedDocsGuidePage,
    NestedDocsIndexPage,
    NestedDocsItemPage,
    NestedDocsLayout,
)
from .pages.nested_dynamic import NestedDynamicPage
from .pages.not_found import NotFound
from .pages.repeat import RepeatPage
from .pages.route_guards import GuardAdminPage, GuardLoginPage, auth_guard
from .pages.scoped_style import ScopedStylePage
from .pages.scroll_restoration import ScrollLongPage, ScrollTargetPage
from .pages.signal import ReactivePage
from .pages.storage import StoragePage
from .pages.storage_tab_sync import StorageTabSyncPage
from .pages.suspense_test import SuspensePage
from .pages.switch_test import SwitchPage
from .pages.teleport import TeleportPage
from .pages.template import TemplatePage
from .pages.template_components import TemplateComponentsPage
from .pages.template_control_flow import TemplateControlFlowPage
from .pages.template_expressions import TemplateExpressionsPage
from .pages.transition import TransitionPage
from .pages.two_way_binding import TwoWayBindingPage
from .pages.window_events import WindowEventsPage

router = Router(
    {"path": "/", "component": HomePage},
    {"path": "/reactive", "component": ReactivePage},
    {"path": "/component", "component": FunctionStylePage},
    {"path": "/component/classstyle", "component": ClassStylePage},
    {"path": "/custom-elements", "component": CustomElementPage},
    {"path": "/event", "component": EventPage},
    {"path": "/window-events", "component": WindowEventsPage},
    {"path": "/switch", "component": SwitchPage},
    {"path": "/repeat", "component": RepeatPage},
    {"path": "/keyed-repeat", "component": KeyedRepeatPage},
    {"path": "/dict-repeat", "component": DictRepeatPage},
    {"path": "/nested-dynamic", "component": NestedDynamicPage},
    {"path": "/lifecycle", "component": LifecyclePage},
    {"path": "/scoped-style", "component": ScopedStylePage},
    {"path": "/scroll-long", "component": ScrollLongPage},
    {"path": "/scroll-target", "component": ScrollTargetPage},
    {"path": "/async-nav", "component": AsyncNavPage},
    {"path": "/suspense", "component": SuspensePage},
    {"path": "/client-only", "component": ClientOnlyPage},
    {"path": "/bundled-deps", "component": BundledDepsPage},
    {"path": "/di-provide", "component": DiProviderWrapper},
    {"path": "/di-inject", "component": DiInjectPage},
    {"path": "/template", "component": TemplatePage},
    {"path": "/template-components", "component": TemplateComponentsPage},
    {"path": "/template-control-flow", "component": TemplateControlFlowPage},
    {"path": "/template-expressions", "component": TemplateExpressionsPage},
    {"path": "/markdown-for", "component": MarkdownForPage},
    {"path": "/html-parser-parity", "component": HtmlParserParityPage},
    {
        "path": "/nested",
        "component": NestedDocsLayout,
        "children": [
            {"path": "", "component": NestedDocsIndexPage},
            {"path": "/guide", "component": NestedDocsGuidePage},
            {"path": "/api", "component": NestedDocsApiPage},
            {"path": "/item/{id}", "component": NestedDocsItemPage, "path_params": [{"id": "1"}, {"id": "2"}]},
            {"path": "/crash", "component": NestedCrashPage},
        ],
    },
    {"path": "/two-way-binding", "component": TwoWayBindingPage},
    {"path": "/teleport", "component": TeleportPage},
    {"path": "/transition", "component": TransitionPage},
    {"path": "/form-fields", "component": FormFieldsPage},
    {"path": "/storage", "component": StoragePage},
    {"path": "/storage-tab-sync", "component": StorageTabSyncPage},
    {"path": "/error-boundary", "component": ErrorBoundaryPage},
    {"path": "/catch-events", "component": CatchEventsPage},
    {"path": "/login", "component": GuardLoginPage},
    {"path": "/admin", "component": GuardAdminPage},
    default=NotFound,
    mode="history",
)

router.before_route_change.append(auth_guard)
