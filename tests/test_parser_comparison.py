"""
Head-to-head: tree-sitter vs regex parsing on realistic SDK header edge cases.

Each test provides a C header fragment that exposes a known regex limitation.
Both parsers run on the same input so the difference is directly visible.
"""

import re
import pytest
from core.sdk_analyzer import SDKAnalysisResult

# The regex patterns from sdk_analyzer.py (copied for direct comparison)
_RE_FUNC_DECL = re.compile(r"^[\w\s\*]+\s+(\w+)\s*\(([^)]*)\)\s*;", re.MULTILINE)
_RE_TYPEDEF_STRUCT = re.compile(r"typedef\s+(?:struct|union)\s*(?:\w+\s*)?\{([^}]*)\}\s*(\w+)\s*;", re.DOTALL)
_RE_TYPEDEF_ENUM = re.compile(r"typedef\s+enum\s*(?:\w+\s*)?\{([^}]*)\}\s*(\w+)\s*;", re.DOTALL)
_RE_DEFINE = re.compile(r"^#define\s+(\w+)\s+(.+)$", re.MULTILINE)


def _regex_parse(code: str) -> SDKAnalysisResult:
    from core.sdk_analyzer import FunctionSignature, TypeDefinition
    result = SDKAnalysisResult()
    for m in _RE_FUNC_DECL.finditer(code):
        result.functions.append(FunctionSignature(name=m.group(1), return_type="", parameters=m.group(2), header_file="test"))
    for m in _RE_TYPEDEF_STRUCT.finditer(code):
        result.types.append(TypeDefinition(name=m.group(2), kind="struct", body=m.group(1), header_file="test"))
    for m in _RE_TYPEDEF_ENUM.finditer(code):
        result.types.append(TypeDefinition(name=m.group(2), kind="enum", body=m.group(1), header_file="test"))
    for m in _RE_DEFINE.finditer(code):
        result.macros[m.group(1)] = m.group(2).strip()
    return result


def _ts_parse(code: str) -> SDKAnalysisResult:
    from core.ts_parser import parse_header
    result = SDKAnalysisResult()
    parse_header(code.encode(), "test.h", result)
    return result


# ─── Edge Case 1: Multi-line function declaration ───────────────────────────

MULTILINE_FUNC = """
HAL_StatusTypeDef
HAL_TIM_PWM_ConfigChannel(
    TIM_HandleTypeDef *htim,
    TIM_OC_InitTypeDef *sConfig,
    uint32_t Channel
);
"""

def test_multiline_function_decl():
    """Regex \\s matches newlines so it accidentally works here.
    Tree-sitter handles it correctly by design."""
    regex_r = _regex_parse(MULTILINE_FUNC)
    ts_r = _ts_parse(MULTILINE_FUNC)

    regex_names = [f.name for f in regex_r.functions]
    ts_names = [f.name for f in ts_r.functions]

    # Both happen to find it — regex via \s matching newlines
    assert "HAL_TIM_PWM_ConfigChannel" in ts_names
    # But regex captures wrong parameters (it stops at first `)` due to [^)]*)
    if regex_r.functions:
        regex_params = regex_r.functions[0].parameters
        ts_params = ts_r.functions[0].parameters
        # Tree-sitter gets full parameter list correctly
        assert "Channel" in ts_params


# ─── Edge Case 2: #ifdef guarded declarations ──────────────────────────────

IFDEF_GUARDED = """
#ifdef HAL_TIM_MODULE_ENABLED

HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *htim);
HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef *htim);

#endif /* HAL_TIM_MODULE_ENABLED */
"""

def test_ifdef_guarded():
    """Both should find functions inside #ifdef. This is a sanity check."""
    regex_r = _regex_parse(IFDEF_GUARDED)
    ts_r = _ts_parse(IFDEF_GUARDED)

    regex_names = [f.name for f in regex_r.functions]
    ts_names = [f.name for f in ts_r.functions]

    # Regex actually works here because the decls are single-line
    assert "HAL_TIM_Base_Init" in regex_names
    assert "HAL_TIM_Base_Init" in ts_names
    assert "HAL_TIM_Base_Start" in ts_names


# ─── Edge Case 3: __attribute__ decorated functions ─────────────────────────

ATTRIBUTED_FUNC = """
__attribute__((weak)) void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim);
__attribute__((deprecated)) HAL_StatusTypeDef HAL_TIM_OC_Init(TIM_HandleTypeDef *htim);
"""

def test_attributed_functions():
    """Regex chokes on __attribute__ prefix. Tree-sitter handles it."""
    regex_r = _regex_parse(ATTRIBUTED_FUNC)
    ts_r = _ts_parse(ATTRIBUTED_FUNC)

    regex_names = [f.name for f in regex_r.functions]
    ts_names = [f.name for f in ts_r.functions]

    # Regex will match the wrong token as the function name
    assert "HAL_TIM_PeriodElapsedCallback" in ts_names
    assert "HAL_TIM_OC_Init" in ts_names


# ─── Edge Case 4: Function-like macros (false positives) ───────────────────

FUNCTION_LIKE_MACRO = """
#define __HAL_TIM_SET_COMPARE(__HANDLE__, __CHANNEL__, __COMPARE__) \\
  (((__HANDLE__)->Instance->CCR1) = (__COMPARE__))

#define IS_TIM_INSTANCE(INSTANCE) (((INSTANCE) == TIM1) || ((INSTANCE) == TIM2))

void HAL_TIM_IRQHandler(TIM_HandleTypeDef *htim);
"""

def test_function_like_macro_not_mistaken():
    """Regex may match #define lines as function declarations. Tree-sitter won't."""
    regex_r = _regex_parse(FUNCTION_LIKE_MACRO)
    ts_r = _ts_parse(FUNCTION_LIKE_MACRO)

    ts_names = [f.name for f in ts_r.functions]
    assert "HAL_TIM_IRQHandler" in ts_names
    # Tree-sitter correctly separates macros from functions
    assert "__HAL_TIM_SET_COMPARE" not in ts_names


# ─── Edge Case 5: Nested struct with function pointer fields ───────────────

NESTED_STRUCT = """
typedef struct {
    uint32_t Mode;
    void (*CallbackFn)(void *context);
    struct {
        uint16_t Priority;
        uint16_t SubPriority;
    } NVIC_Config;
} Complex_InitTypeDef;
"""

def test_nested_struct():
    """Regex with [^}] stops at the inner closing brace. Tree-sitter gets the full body."""
    regex_r = _regex_parse(NESTED_STRUCT)
    ts_r = _ts_parse(NESTED_STRUCT)

    regex_types = [t.name for t in regex_r.types]
    ts_types = [t.name for t in ts_r.types]

    assert "Complex_InitTypeDef" in ts_types
    # Regex fails because [^}] stops at the inner struct's }
    assert "Complex_InitTypeDef" not in regex_types, "Regex should fail on nested structs"


# ─── Edge Case 6: Pointer-returning function ───────────────────────────────

POINTER_RETURN = """
TIM_HandleTypeDef* HAL_TIM_GetHandle(uint32_t instance);
const char *HAL_GetErrorString(HAL_StatusTypeDef status);
"""

def test_pointer_return():
    """Both should handle pointer return types, but regex may split the type wrong."""
    ts_r = _ts_parse(POINTER_RETURN)
    ts_names = [f.name for f in ts_r.functions]

    assert "HAL_TIM_GetHandle" in ts_names
    assert "HAL_GetErrorString" in ts_names


# ─── Edge Case 7: Enum with trailing comma (common in HAL) ─────────────────

TRAILING_COMMA_ENUM = """
typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U,
} HAL_StatusTypeDef;
"""

def test_trailing_comma_enum():
    """Both should handle trailing comma in enum."""
    regex_r = _regex_parse(TRAILING_COMMA_ENUM)
    ts_r = _ts_parse(TRAILING_COMMA_ENUM)

    assert "HAL_StatusTypeDef" in [t.name for t in ts_r.types]
    assert "HAL_StatusTypeDef" in [t.name for t in regex_r.types]


# ─── Edge Case 8: Multiline #define with backslash continuation ────────────

MULTILINE_DEFINE = r"""
#define UNUSED(X) (void)X

#define HAL_MAX_DELAY  0xFFFFFFFFU

#define __HAL_LOCK(__HANDLE__) \
  do { \
    if ((__HANDLE__)->Lock == HAL_LOCKED) return HAL_BUSY; \
    (__HANDLE__)->Lock = HAL_LOCKED; \
  } while(0)
"""

def test_multiline_define():
    """Tree-sitter handles both simple and function-like macros."""
    regex_r = _regex_parse(MULTILINE_DEFINE)
    ts_r = _ts_parse(MULTILINE_DEFINE)

    assert "HAL_MAX_DELAY" in ts_r.macros
    assert "HAL_MAX_DELAY" in regex_r.macros
    # Tree-sitter also finds function-like macros via preproc_function_def
    assert "UNUSED" in ts_r.macros


# ─── Summary helper ────────────────────────────────────────────────────────

def test_summary_comparison():
    """Run both parsers on all edge cases and print a comparison table."""
    all_code = "\n".join([
        MULTILINE_FUNC, IFDEF_GUARDED, ATTRIBUTED_FUNC,
        FUNCTION_LIKE_MACRO, NESTED_STRUCT, POINTER_RETURN,
        TRAILING_COMMA_ENUM, MULTILINE_DEFINE,
    ])

    regex_r = _regex_parse(all_code)
    ts_r = _ts_parse(all_code)

    print("\n" + "=" * 70)
    print("TREE-SITTER vs REGEX COMPARISON")
    print("=" * 70)
    print(f"  Functions: tree-sitter={len(ts_r.functions):>3}  regex={len(regex_r.functions):>3}")
    print(f"  Types:     tree-sitter={len(ts_r.types):>3}  regex={len(regex_r.types):>3}")
    print(f"  Macros:    tree-sitter={len(ts_r.macros):>3}  regex={len(regex_r.macros):>3}")
    print()

    ts_func_names = {f.name for f in ts_r.functions}
    regex_func_names = {f.name for f in regex_r.functions}

    only_ts = ts_func_names - regex_func_names
    only_regex = regex_func_names - ts_func_names
    if only_ts:
        print(f"  Functions ONLY tree-sitter found: {only_ts}")
    if only_regex:
        print(f"  Functions ONLY regex found (likely false positives): {only_regex}")

    ts_type_names = {t.name for t in ts_r.types}
    regex_type_names = {t.name for t in regex_r.types}
    only_ts_types = ts_type_names - regex_type_names
    if only_ts_types:
        print(f"  Types ONLY tree-sitter found: {only_ts_types}")
    print("=" * 70)

    # Tree-sitter should always find >= what regex finds for legitimate symbols
    assert len(ts_r.functions) >= len(regex_r.functions)
