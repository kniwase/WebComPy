from typing import (Any, Dict, List, Tuple, Union)
from browser import html, document
from .node import VNode, VTextNode


def generate_node_mapping(nodes: List[Any],
                          parents: Tuple[int, ...],
                          mapping: Dict[Tuple[int, ...], Any]):
    for idx, node in enumerate(nodes):
        current: Tuple[int, ...] = (*parents, idx)
        mapping[current] = node
        generate_node_mapping(node.child_nodes, current, mapping)
    return mapping


def generate_rnode_mapping(nodes: List[Any]):
    return generate_node_mapping(nodes, tuple(), {})


def update_dom(root: Any,
               vdom_mapping: Dict[Tuple[int, ...], Union[VNode, VTextNode]],
               rdom_mapping: Dict[Tuple[int, ...], Any]):
    refs: Dict[str, Any] = {}
    mapping = ((idxs, rdom_mapping.get(idxs), vnode)
               for idxs, vnode in vdom_mapping.items())
    for idxs, rnode, vnode in mapping:
        if rnode and rnode.isConnected:
            if vnode.rnode and id(rnode) == id(vnode.rnode):
                update_node(rnode, vnode, refs)
            else:
                replace_node(rnode, vnode, refs)
        else:
            insert_node(root, vnode, idxs, refs)

    nodes_to_delete = (rnode
                       for idxs, rnode in rdom_mapping.items()
                       if idxs not in vdom_mapping)
    for rnode in nodes_to_delete:
        delete_node(rnode)

    return refs


def update_node(rnode: Any,
                vnode: Union[VNode, VTextNode],
                refs: Dict[str, Any]):
    if isinstance(vnode, VNode):
        # Update attributes
        for k, v in vnode.attrs.items():
            k = k.lower()
            if k not in rnode.attrs or rnode.attrs[k] != v:
                rnode.attrs[k] = v
        for k in list(rnode.attrs.keys()):
            if k not in {k.lower() for k in vnode.attrs}:
                del rnode.attrs[k]
        if 'ref' in rnode.attrs:
            refs[rnode.attrs['ref']] = rnode
    else:
        if rnode.text != vnode.text:
            rnode.text = vnode.text


def create_node(vnode: Union[VNode, VTextNode],
                refs: Dict[str, Any]):
    if isinstance(vnode, VNode):
        attrs = {k: v for k, v in vnode.attrs.items() if k != 'style'}
        node = html.maketag(vnode.tag)(**attrs)
        for k, v in vnode.attrs.items():
            if k == 'style':
                node.attrs[k] = v
        for event_name, callback in vnode.event_callbacks.items():
            node.bind(event_name, callback)
        for key, value in vnode.attrs.items():
            if key == 'ref' and isinstance(value, str):
                refs[value] = node
    else:
        node = document.createTextNode(vnode.text)
    vnode.rnode = node
    return node


def replace_node(rnode: Any,
                 vnode: Union[VNode, VTextNode],
                 refs: Dict[str, Any]):
    node = create_node(vnode, refs)
    rnode.parentNode.replaceChild(node, rnode)


def get_target_node(root: Any, idxs: Tuple[int, ...]):
    parent = root
    for idx in idxs[:-1]:
        parent = parent.child_nodes[idx]
    return parent, len(parent.child_nodes)


def insert_node(root: Any,
                vnode: Union[VNode, VTextNode],
                idxs: Tuple[int, ...],
                refs: Dict[str, Any]):
    parent, parent_node_count = get_target_node(root, idxs)
    node = create_node(vnode, refs)
    if parent_node_count == idxs[-1]:
        parent.appendChild(node)
    else:
        parent.insertBefore(node, parent.child_nodes[idxs[-1]])


def delete_node(rnode: Any):
    rnode.remove()
    del rnode
