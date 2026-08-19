"""Tests for Phase 3: session persistence, build sandbox, build templates."""

import tempfile
from pathlib import Path


def test_session_store_roundtrip():
    from server.session_store import SessionStore
    from core.workflow import WorkflowState, WorkflowStage

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = SessionStore(db_path=db_path)

    state = WorkflowState(
        user_input="LED blink on PA5",
        board_name="NUCLEO-F446RE",
        stage=WorkflowStage.HARDWARE,
    )
    state.requirements = {"peripheral_type": "GPIO", "description": "LED blink"}

    store[state.session_id] = state

    assert state.session_id in store
    loaded = store[state.session_id]
    assert loaded.user_input == "LED blink on PA5"
    assert loaded.board_name == "NUCLEO-F446RE"
    assert loaded.stage == WorkflowStage.HARDWARE
    assert loaded.requirements["peripheral_type"] == "GPIO"

    store.close()
    db_path.unlink(missing_ok=True)


def test_session_store_list():
    from server.session_store import SessionStore
    from core.workflow import WorkflowState, WorkflowStage

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = SessionStore(db_path=db_path)

    for i in range(3):
        s = WorkflowState(user_input=f"req {i}", board_name="BOARD")
        store[s.session_id] = s

    sessions = store.list_sessions()
    assert len(sessions) == 3
    assert all("session_id" in s for s in sessions)

    store.close()
    db_path.unlink(missing_ok=True)


def test_session_store_persistence():
    """Verify data survives a new SessionStore instance on the same DB."""
    from server.session_store import SessionStore
    from core.workflow import WorkflowState, WorkflowStage

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store1 = SessionStore(db_path=db_path)
    state = WorkflowState(user_input="persist test", board_name="BOARD")
    sid = state.session_id
    store1[sid] = state
    store1.close()

    store2 = SessionStore(db_path=db_path)
    assert sid in store2
    loaded = store2[sid]
    assert loaded.user_input == "persist test"
    store2.close()

    db_path.unlink(missing_ok=True)


def test_build_sandbox():
    from core.build_sandbox import sandboxed_run
    import sys

    result = sandboxed_run(
        [sys.executable, "-c", "print('hello')"],
        timeout=10,
    )
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]
    assert not result["timed_out"]


def test_build_sandbox_timeout():
    from core.build_sandbox import sandboxed_run
    import sys

    result = sandboxed_run(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        timeout=1,
    )
    assert result["timed_out"]
    assert result["returncode"] == -1


def test_build_sandbox_missing_command():
    from core.build_sandbox import sandboxed_run

    result = sandboxed_run(["nonexistent-binary-xyz"], timeout=5)
    assert result["returncode"] == -1
    assert "not found" in result["stderr"].lower()


def test_cmake_generation():
    from core.build_templates import generate_cmake

    cmake = generate_cmake(
        project_name="blinky",
        source_files=["main.c", "stm32f4xx_it.c"],
        target_mcu="STM32F446",
        sdk_include_paths=["Inc", "Drivers/STM32F4xx_HAL_Driver/Inc"],
    )

    assert "cmake_minimum_required" in cmake
    assert "project(blinky" in cmake
    assert "main.c" in cmake
    assert "cortex-m4" in cmake
    assert "arm-none-eabi-gcc" in cmake


def test_makefile_generation():
    from core.build_templates import generate_makefile

    makefile = generate_makefile(
        project_name="blinky",
        source_files=["main.c", "stm32f4xx_it.c"],
        target_mcu="STM32F446",
        sdk_include_paths=["Inc"],
        linker_script="STM32F446RETx_FLASH.ld",
    )

    assert "PROJECT = blinky" in makefile
    assert "arm-none-eabi-gcc" in makefile
    assert "main.o" in makefile
    assert "LDSCRIPT" in makefile
    assert ".PHONY" in makefile
