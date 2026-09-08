; TypeScript tags. Derived from tree-sitter/tree-sitter-typescript queries/tags.scm
; (MIT), which omits class_declaration and function_declaration entirely.
;
; Definitions only; see python/tags.scm for why @reference.call is left out.
;
; Declarations are matched unanchored because `export` wraps them in an
; export_statement, so anchoring to the program node would miss every exported
; symbol -- which in practice is most of them.

; ── classes ──────────────────────────────────────────────────────────────────

(class_declaration
  name: (type_identifier) @name) @definition.class

(abstract_class_declaration
  name: (type_identifier) @name) @definition.class

; ── interfaces ───────────────────────────────────────────────────────────────

(interface_declaration
  name: (type_identifier) @name) @definition.interface

; ── enums ────────────────────────────────────────────────────────────────────

(enum_declaration
  name: (identifier) @name) @definition.enum

; ── type aliases ─────────────────────────────────────────────────────────────

(type_alias_declaration
  name: (type_identifier) @name) @definition.type

; ── namespaces ───────────────────────────────────────────────────────────────

(internal_module
  name: (identifier) @name) @definition.module

; ── functions ────────────────────────────────────────────────────────────────
; One pattern covers sync and async: `async` is an optional token inside
; function_declaration.

(function_declaration
  name: (identifier) @name) @definition.function

(generator_function_declaration
  name: (identifier) @name) @definition.function

(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [
      (arrow_function)
      (function_expression)
    ])) @definition.function

; ── constructors ─────────────────────────────────────────────────────────────

(method_definition
  name: (property_identifier) @name
  (#eq? @name "constructor")) @definition.class_init

; ── methods ──────────────────────────────────────────────────────────────────

(method_definition
  name: (property_identifier) @name
  (#not-eq? @name "constructor")) @definition.method

; ── constants ────────────────────────────────────────────────────────────────

(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [
      (number)
      (string)
      (template_string)
      (true)
      (false)
      (object)
      (array)
      (as_expression)
      (call_expression)
    ]
    (#match? @name "^[A-Z][A-Z0-9_]*$"))) @definition.constant

(public_field_definition
  name: (property_identifier) @name
  (#match? @name "^[A-Z][A-Z0-9_]*$")) @definition.class_constant
