"""
Tree-sitter C Parser — replaces regex-based header parsing with proper AST.

Handles multi-line declarations, #ifdef guards, attribute-decorated functions,
and nested structs that regex cannot reliably parse.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import tree_sitter_c as tsc
from tree_sitter import Language, Parser

from core.sdk_analyzer import FunctionSignature, SDKAnalysisResult, TypeDefinition

logger = logging.getLogger(__name__)

C_LANGUAGE = Language(tsc.language())

_parser = Parser(C_LANGUAGE)


def parse_header(content: bytes, header_name: str, result: SDKAnalysisResult) -> None:
    """Parse a C header file using tree-sitter and append results."""
    tree = _parser.parse(content)
    result.headers_scanned += 1

    _walk(tree.root_node, content, header_name, result)


def _walk(node, source: bytes, header_name: str, result: SDKAnalysisResult) -> None:
    for child in node.children:
        if child.type == "declaration":
            _try_extract_function_decl(child, source, header_name, result)
        elif child.type == "type_definition":
            _try_extract_typedef(child, source, header_name, result)
        elif child.type == "preproc_def":
            _try_extract_macro(child, source, result)
        elif child.type in ("preproc_ifdef", "preproc_if", "preproc_else", "translation_unit"):
            _walk(child, source, header_name, result)


def _node_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _try_extract_function_decl(node, source: bytes, header_name: str, result: SDKAnalysisResult) -> None:
    """Extract function declarations (not definitions — those have a body)."""
    declarator = None
    for child in node.children:
        if child.type == "function_declarator":
            declarator = child
            break
        if child.type in ("pointer_declarator", "attributed_declarator"):
            for sub in _find_nodes(child, "function_declarator"):
                declarator = sub
                break

    if declarator is None:
        return

    name_node = None
    params_node = None
    for child in declarator.children:
        if child.type == "identifier":
            name_node = child
        elif child.type == "parameter_list":
            params_node = child

    if name_node is None:
        return

    name = _node_text(name_node, source)
    params = _node_text(params_node, source).strip("()") if params_node else ""

    full_text = _node_text(node, source)
    ret_end = full_text.find(name)
    ret_type = full_text[:ret_end].strip().rstrip("*").strip() if ret_end > 0 else ""
    # Re-include pointer stars
    stars = full_text[:ret_end].count("*")
    if stars:
        ret_type += " " + "*" * stars

    result.functions.append(FunctionSignature(
        name=name,
        return_type=ret_type.strip(),
        parameters=params.strip(),
        header_file=header_name,
    ))


def _try_extract_typedef(node, source: bytes, header_name: str, result: SDKAnalysisResult) -> None:
    """Extract typedef struct/union/enum definitions."""
    type_node = None
    name_node = None

    for child in node.children:
        if child.type in ("struct_specifier", "union_specifier"):
            type_node = child
        elif child.type == "enum_specifier":
            type_node = child
        elif child.type == "type_identifier":
            name_node = child

    if type_node is None or name_node is None:
        return

    kind = "enum" if type_node.type == "enum_specifier" else "struct"
    if type_node.type == "union_specifier":
        kind = "union"

    body_node = None
    for child in type_node.children:
        if child.type in ("field_declaration_list", "enumerator_list"):
            body_node = child
            break

    body = _node_text(body_node, source).strip("{}").strip() if body_node else ""
    name = _node_text(name_node, source)

    result.types.append(TypeDefinition(
        name=name,
        kind=kind,
        body=body,
        header_file=header_name,
    ))


def _try_extract_macro(node, source: bytes, result: SDKAnalysisResult) -> None:
    name_node = None
    value_node = None
    for child in node.children:
        if child.type == "identifier" and name_node is None:
            name_node = child
        elif child.type == "preproc_arg":
            value_node = child

    if name_node:
        name = _node_text(name_node, source)
        value = _node_text(value_node, source).strip() if value_node else ""
        result.macros[name] = value


def _find_nodes(node, target_type: str):
    """Recursively find all descendants of a given type."""
    if node.type == target_type:
        yield node
    for child in node.children:
        yield from _find_nodes(child, target_type)
