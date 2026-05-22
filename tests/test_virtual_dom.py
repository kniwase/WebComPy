from __future__ import annotations

from webcompy.ports._server._virtual_dom import VirtualDOMEvent, VirtualDOMNode


class TestVirtualDOMNodeConstruction:
    def test_element_node(self):
        node = VirtualDOMNode("div")
        assert node.nodeName == "DIV"
        assert node.nodeType == 1
        assert node.textContent == ""
        assert node.__webcompy_node__ is True
        assert node.__webcompy_prerendered_node__ is False

    def test_text_node(self):
        node = VirtualDOMNode("#text", node_type=3, text_content="hello")
        assert node.nodeName == "#text"
        assert node.nodeType == 3
        assert node.textContent == "hello"

    def test_initial_children_empty(self):
        node = VirtualDOMNode("div")
        assert node.childNodes.length == 0
        assert list(node.childNodes) == []

    def test_initial_no_parent(self):
        node = VirtualDOMNode("div")
        assert node.parentNode is None

    def test_initial_no_attributes(self):
        node = VirtualDOMNode("div")
        assert node.getAttributeNames() == []
        assert node.hasAttribute("id") is False

    def test_initial_no_event_listeners(self):
        node = VirtualDOMNode("div")
        assert node._event_listeners == []


class TestVirtualDOMNodeTreeOperations:
    def test_append_child(self):
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        parent.appendChild(child)
        assert parent.childNodes.length == 1
        assert parent.childNodes[0] is child
        assert child.parentNode is parent

    def test_append_child_removes_from_previous_parent(self):
        p1 = VirtualDOMNode("div")
        p2 = VirtualDOMNode("section")
        child = VirtualDOMNode("span")
        p1.appendChild(child)
        p2.appendChild(child)
        assert p1.childNodes.length == 0
        assert p2.childNodes.length == 1
        assert child.parentNode is p2

    def test_remove_child(self):
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        parent.appendChild(child)
        parent.removeChild(child)
        assert parent.childNodes.length == 0
        assert child.parentNode is None

    def test_insert_before(self):
        parent = VirtualDOMNode("div")
        c1 = VirtualDOMNode("span")
        c2 = VirtualDOMNode("p")
        parent.appendChild(c1)
        parent.insertBefore(c2, c1)
        assert parent.childNodes.length == 2
        assert parent.childNodes[0] is c2
        assert parent.childNodes[1] is c1
        assert c2.parentNode is parent

    def test_insert_before_removes_from_previous_parent(self):
        p1 = VirtualDOMNode("div")
        p2 = VirtualDOMNode("section")
        child = VirtualDOMNode("span")
        ref = VirtualDOMNode("p")
        p1.appendChild(child)
        p2.appendChild(ref)
        p2.insertBefore(child, ref)
        assert p1.childNodes.length == 0
        assert child.parentNode is p2

    def test_replace_child(self):
        parent = VirtualDOMNode("div")
        old = VirtualDOMNode("span")
        new = VirtualDOMNode("p")
        parent.appendChild(old)
        parent.replaceChild(new, old)
        assert parent.childNodes.length == 1
        assert parent.childNodes[0] is new
        assert new.parentNode is parent
        assert old.parentNode is None

    def test_replace_child_removes_new_from_previous_parent(self):
        p1 = VirtualDOMNode("div")
        p2 = VirtualDOMNode("section")
        old = VirtualDOMNode("span")
        new = VirtualDOMNode("p")
        p2.appendChild(old)
        p1.appendChild(new)
        p2.replaceChild(new, old)
        assert p1.childNodes.length == 0
        assert new.parentNode is p2

    def test_remove(self):
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        parent.appendChild(child)
        child.remove()
        assert parent.childNodes.length == 0
        assert child.parentNode is None

    def test_remove_no_parent(self):
        child = VirtualDOMNode("span")
        child.remove()
        assert child.parentNode is None


class TestVirtualDOMNodeAttributes:
    def test_set_and_get_attribute(self):
        node = VirtualDOMNode("div")
        node.setAttribute("class", "foo")
        assert node.getAttribute("class") == "foo"
        assert node.hasAttribute("class") is True

    def test_get_attribute_missing(self):
        node = VirtualDOMNode("div")
        assert node.getAttribute("class") is None

    def test_remove_attribute(self):
        node = VirtualDOMNode("div")
        node.setAttribute("class", "foo")
        node.removeAttribute("class")
        assert node.hasAttribute("class") is False
        assert node.getAttribute("class") is None

    def test_get_attribute_names(self):
        node = VirtualDOMNode("div")
        node.setAttribute("id", "main")
        node.setAttribute("class", "foo")
        names = node.getAttributeNames()
        assert "id" in names
        assert "class" in names

    def test_set_attribute_none_value(self):
        node = VirtualDOMNode("div")
        node._attributes["disabled"] = None
        assert node.getAttribute("disabled") is None
        assert node.hasAttribute("disabled") is True


class TestVirtualDOMNodeTextContent:
    def test_set_text_content(self):
        node = VirtualDOMNode("#text", node_type=3, text_content="old")
        node.textContent = "new"
        assert node.textContent == "new"

    def test_text_content_element_node(self):
        node = VirtualDOMNode("div")
        node.textContent = "hello"
        assert node.textContent == "hello"


class TestVirtualDOMNodeChildNodes:
    def test_child_nodes_list(self):
        parent = VirtualDOMNode("div")
        c1 = VirtualDOMNode("span")
        c2 = VirtualDOMNode("p")
        parent.appendChild(c1)
        parent.appendChild(c2)
        assert parent.childNodes.length == 2
        assert parent.childNodes[0] is c1
        assert parent.childNodes[1] is c2

    def test_child_nodes_iterable(self):
        parent = VirtualDOMNode("div")
        c1 = VirtualDOMNode("span")
        c2 = VirtualDOMNode("p")
        parent.appendChild(c1)
        parent.appendChild(c2)
        result = list(parent.childNodes)
        assert result == [c1, c2]

    def test_child_nodes_len(self):
        parent = VirtualDOMNode("div")
        c1 = VirtualDOMNode("span")
        parent.appendChild(c1)
        assert len(parent.childNodes) == 1


class TestVirtualDOMNodeEventListeners:
    def test_add_event_listener(self):
        node = VirtualDOMNode("div")
        handler = lambda e: None
        node.addEventListener("click", handler)
        assert ("click", handler) in node._event_listeners

    def test_remove_event_listener(self):
        node = VirtualDOMNode("div")
        handler = lambda e: None
        node.addEventListener("click", handler)
        node.removeEventListener("click", handler)
        assert ("click", handler) not in node._event_listeners

    def test_multiple_event_listeners(self):
        node = VirtualDOMNode("div")
        h1 = lambda e: None
        h2 = lambda e: None
        node.addEventListener("click", h1)
        node.addEventListener("click", h2)
        assert len(node._event_listeners) == 2


class TestVirtualDOMNodeDispatchEvent:
    def test_dispatch_calls_handler(self):
        node = VirtualDOMNode("div")
        called = []
        node.addEventListener("click", lambda e: called.append(e))
        event = VirtualDOMEvent("click")
        result = node.dispatchEvent(event)
        assert len(called) == 1
        assert result is True

    def test_dispatch_sets_target_and_phase(self):
        node = VirtualDOMNode("div")
        node.addEventListener("click", lambda e: None)
        event = VirtualDOMEvent("click")
        node.dispatchEvent(event)
        assert event._target is node
        assert event._current_target is node
        assert event._event_phase == 2

    def test_dispatch_bubbling(self):
        grandparent = VirtualDOMNode("div")
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        grandparent.appendChild(parent)
        parent.appendChild(child)

        gp_called = []
        parent_called = []
        child_called = []

        grandparent.addEventListener("click", lambda e: gp_called.append(e))
        parent.addEventListener("click", lambda e: parent_called.append(e))
        child.addEventListener("click", lambda e: child_called.append(e))

        event = VirtualDOMEvent("click", bubbles=True)
        child.dispatchEvent(event)

        assert len(child_called) == 1
        assert len(parent_called) == 1
        assert len(gp_called) == 1
        assert event._event_phase == 3

    def test_dispatch_no_bubbling(self):
        grandparent = VirtualDOMNode("div")
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        grandparent.appendChild(parent)
        parent.appendChild(child)

        gp_called = []
        parent_called = []
        child_called = []

        grandparent.addEventListener("click", lambda e: gp_called.append(e))
        parent.addEventListener("click", lambda e: parent_called.append(e))
        child.addEventListener("click", lambda e: child_called.append(e))

        event = VirtualDOMEvent("click", bubbles=False)
        child.dispatchEvent(event)

        assert len(child_called) == 1
        assert len(parent_called) == 0
        assert len(gp_called) == 0

    def test_dispatch_stop_propagation(self):
        parent = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        parent.appendChild(child)

        gp_called = []

        def stop_handler(e):
            e.stopPropagation()

        parent.addEventListener("click", lambda e: gp_called.append(e))
        child.addEventListener("click", stop_handler)

        event = VirtualDOMEvent("click", bubbles=True)
        child.dispatchEvent(event)

        assert len(gp_called) == 0

    def test_dispatch_prevent_default(self):
        node = VirtualDOMNode("div")
        node.addEventListener("click", lambda e: e.preventDefault())
        event = VirtualDOMEvent("click", cancelable=True)
        result = node.dispatchEvent(event)
        assert event._default_prevented is True
        assert result is False

    def test_dispatch_prevent_default_not_cancelable(self):
        node = VirtualDOMNode("div")
        node.addEventListener("click", lambda e: e.preventDefault())
        event = VirtualDOMEvent("click", cancelable=False)
        result = node.dispatchEvent(event)
        assert event._default_prevented is False
        assert result is True

    def test_dispatch_returns_not_default_prevented(self):
        node = VirtualDOMNode("div")
        event = VirtualDOMEvent("click")
        result = node.dispatchEvent(event)
        assert result is True

    def test_dispatch_no_matching_listener(self):
        node = VirtualDOMNode("div")
        node.addEventListener("click", lambda e: None)
        event = VirtualDOMEvent("submit")
        result = node.dispatchEvent(event)
        assert result is True


class TestVirtualDOMEvent:
    def test_event_type(self):
        event = VirtualDOMEvent("click")
        assert event.type == "click"

    def test_event_bubbles(self):
        event = VirtualDOMEvent("click", bubbles=True)
        assert event.bubbles is True

    def test_event_cancelable(self):
        event = VirtualDOMEvent("click", cancelable=True)
        assert event.cancelable is True

    def test_event_initial_state(self):
        event = VirtualDOMEvent("click")
        assert event.defaultPrevented is False
        assert event.eventPhase == 0
        assert event.target is None
        assert event.currentTarget is None

    def test_prevent_default_cancelable(self):
        event = VirtualDOMEvent("click", cancelable=True)
        event.preventDefault()
        assert event.defaultPrevented is True

    def test_prevent_default_not_cancelable(self):
        event = VirtualDOMEvent("click", cancelable=False)
        event.preventDefault()
        assert event.defaultPrevented is False

    def test_stop_propagation(self):
        event = VirtualDOMEvent("click")
        event.stopPropagation()
        assert event._propagation_stopped is True

    def test_time_stamp(self):
        event = VirtualDOMEvent("click")
        assert isinstance(event.timeStamp, int)
        assert event.timeStamp > 0

    def test_getattr_returns_none(self):
        event = VirtualDOMEvent("click")
        assert event.some_random_attr is None
