from webcompy.elements import html
from webcompy.components import define_component, ComponentContext
from webcompy.router import RouterContext
from ...components.demo_display import DemoDisplay
from ...templates.demo.todo import ToDoList


@define_component
def ToDoListPage(_: ComponentContext[RouterContext]):
    return html.DIV(
        {},
        DemoDisplay(
            {
                "title": "ToDo List",
                "code": """
                    from typing import Any, TypedDict
                    from webcompy.elements import html, repeat, DomNodeRef
                    from webcompy.components import define_component, ComponentContext
                    from webcompy.reactive import Reactive, ReactiveList, computed


                    class TodoData(TypedDict):
                        title: Reactive[str]
                        done: Reactive[bool]


                    @define_component
                    def ToDoItem(context: ComponentContext[TodoData]):
                        input_ref = DomNodeRef()

                        def on_change_state(_: Any):
                            context.props["done"].value = input_ref.node.checked

                        return html.LI(
                            {},
                            html.LABEL(
                                {},
                                html.INPUT(
                                    {
                                        "type": "checkbox",
                                        "@change": on_change_state,
                                        ":ref": input_ref,
                                    },
                                ),
                            ),
                            " ",
                            html.SPAN(
                                {
                                    "style": computed(
                                        lambda: "text-decoration: line-through;"
                                        if context.props["done"].value
                                        else ""
                                    )
                                },
                                context.props["title"],
                            ),
                        )


                    ToDoItem.scoped_style = {
                        "li": {
                            "color": "#2d8fdd",
                            "border-left": " solid 6px #2d8fdd",
                            "background": "#f1f8ff",
                            "line-height": "1.5",
                            "margin": "5px",
                            "padding": "5px",
                            "vertical-align": "middle",
                            "list-style-type": "none",
                        }
                    }


                    @define_component
                    def ToDoList(_: ComponentContext[None]):
                        input_ref = DomNodeRef()
                        data: ReactiveList[TodoData] = ReactiveList(
                            [
                                {
                                    "title": Reactive("Try WebComPy"),
                                    "done": Reactive(False),
                                },
                                {
                                    "title": Reactive("Create WebComPy project"),
                                    "done": Reactive(False),
                                }
                            ]
                        )

                        def append_item(_: Any):
                            title = input_ref.node.value
                            if title:
                                data.append(
                                    {
                                        "title": Reactive(title),
                                        "done": Reactive(False),
                                    }
                                )

                        def remove_done_items(_: Any):
                            items_remove = reversed(
                                [idx for idx, item in enumerate(data.value) if item["done"].value]
                            )
                            for idx in items_remove:
                                data.pop(idx)

                        return html.DIV(
                            {},
                            html.P(
                                {},
                                "Title: ",
                                html.INPUT({":ref": input_ref}),
                                html.BUTTON({"@click": append_item}, "Add ToDo"),
                                html.BUTTON({"@click": remove_done_items}, "Remove Done Items"),
                            ),
                            html.UL(
                                {},
                                repeat(
                                    sequence=data,
                                    template=ToDoItem,
                                ),
                            ),
                        )


                    ToDoList.scoped_style = {
                        "button": {
                            "display": "inline-block",
                            "text-decoration": "none",
                            "border": "solid 2px #668ad8",
                            "border-radius": "3px",
                            "transition": "0.2s",
                            "color": "black",
                        },
                        "button:hover": {
                            "background": "#668ad8",
                            "color": "white",
                        },
                    }""",
            },
            slots={"component": lambda: ToDoList(None)},
        ),
    )
