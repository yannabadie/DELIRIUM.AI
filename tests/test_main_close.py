from types import SimpleNamespace

import multiprocessing.process as mp_process

import src.main as main_module
from src.main import Delirium
from src.process_cleanup import (
    RUNNING_PROCESS_CLOSE_ERROR,
    install_safe_multiprocessing_close,
    safe_close_process,
)


class DummyChild:
    def __init__(
        self,
        alive: bool,
        survives_terminate: bool = False,
        close_exc: Exception | None = None,
    ):
        self.pid = 1234
        self._alive = alive
        self._survives_terminate = survives_terminate
        self._close_exc = close_exc
        self.join_calls = []
        self.terminated = False
        self.closed = False

    def join(self, timeout=None):
        self.join_calls.append(timeout)

    def is_alive(self):
        return self._alive

    def terminate(self):
        self.terminated = True
        if not self._survives_terminate:
            self._alive = False

    def close(self):
        if self._close_exc is not None:
            raise self._close_exc
        self.closed = True


def test_delirium_close_drains_lingering_child_processes(monkeypatch):
    child = DummyChild(alive=True)
    monkeypatch.setattr("src.process_cleanup.multiprocessing.active_children", lambda: [child])

    delirium = Delirium.__new__(Delirium)
    delirium.async_llm = SimpleNamespace(close=lambda: None)
    delirium.llm = SimpleNamespace(close=lambda: None)
    episodic_closed = {"value": False}
    delirium.episodic = SimpleNamespace(close=lambda: episodic_closed.__setitem__("value", True))

    delirium.close()

    assert child.join_calls == [0.2, 1.0]
    assert child.terminated is True
    assert child.closed is True
    assert episodic_closed["value"] is True


def test_delirium_close_keeps_clean_child_processes_untouched(monkeypatch):
    child = DummyChild(alive=False)
    monkeypatch.setattr("src.process_cleanup.multiprocessing.active_children", lambda: [child])

    delirium = Delirium.__new__(Delirium)
    delirium.async_llm = SimpleNamespace(close=lambda: None)
    delirium.llm = SimpleNamespace(close=lambda: None)
    delirium.episodic = SimpleNamespace(close=lambda: None)

    delirium.close()

    assert child.join_calls == []
    assert child.terminated is False
    assert child.closed is True


def test_delirium_close_skips_close_for_child_still_running_after_terminate(monkeypatch):
    child = DummyChild(alive=True, survives_terminate=True)
    monkeypatch.setattr("src.process_cleanup.multiprocessing.active_children", lambda: [child])

    delirium = Delirium.__new__(Delirium)
    delirium.async_llm = SimpleNamespace(close=lambda: None)
    delirium.llm = SimpleNamespace(close=lambda: None)
    episodic_closed = {"value": False}
    delirium.episodic = SimpleNamespace(close=lambda: episodic_closed.__setitem__("value", True))

    delirium.close()

    assert child.join_calls == [0.2, 1.0]
    assert child.terminated is True
    assert child.closed is False
    assert episodic_closed["value"] is True


def test_delirium_close_ignores_running_process_race_from_close(monkeypatch):
    child = DummyChild(alive=False, close_exc=ValueError(RUNNING_PROCESS_CLOSE_ERROR))
    monkeypatch.setattr("src.process_cleanup.multiprocessing.active_children", lambda: [child])

    delirium = Delirium.__new__(Delirium)
    delirium.async_llm = SimpleNamespace(close=lambda: None)
    delirium.llm = SimpleNamespace(close=lambda: None)
    episodic_closed = {"value": False}
    delirium.episodic = SimpleNamespace(close=lambda: episodic_closed.__setitem__("value", True))

    delirium.close()

    assert child.join_calls == [0.2]
    assert child.terminated is False
    assert child.closed is False
    assert episodic_closed["value"] is True


def test_safe_close_process_terminates_then_retries_close():
    child = DummyChild(alive=True)

    def original_close(process):
        if process.is_alive():
            raise ValueError(RUNNING_PROCESS_CLOSE_ERROR)
        process.closed = True

    closed = safe_close_process(child, original_close)

    assert closed is True
    assert child.join_calls == [0.2, 1.0]
    assert child.terminated is True
    assert child.closed is True


def test_safe_close_process_skips_close_when_child_survives_terminate():
    child = DummyChild(alive=True, survives_terminate=True)

    def original_close(process):
        if process.is_alive():
            raise ValueError(RUNNING_PROCESS_CLOSE_ERROR)
        process.closed = True

    closed = safe_close_process(child, original_close)

    assert closed is False
    assert child.join_calls == [0.2, 1.0]
    assert child.terminated is True
    assert child.closed is False


def test_product_safe_close_wraps_prior_runtime_wrapper(monkeypatch):
    original_close = getattr(mp_process.BaseProcess.close, "_delirium_safe_close_original", None)
    assert original_close is not None

    monkeypatch.setattr(mp_process.BaseProcess, "close", original_close)

    def runtime_close(process):
        return original_close(process)

    runtime_close._delirium_safe_close = True
    runtime_close._delirium_safe_close_source = "grader_runtime"
    runtime_close._delirium_safe_close_original = original_close

    monkeypatch.setattr(mp_process.BaseProcess, "close", runtime_close)
    install_safe_multiprocessing_close()

    product_close = mp_process.BaseProcess.close
    assert getattr(product_close, "_delirium_safe_close_source", None) == "product"
    assert getattr(product_close, "_delirium_safe_close_previous", None) is runtime_close
    assert getattr(product_close, "_delirium_safe_close_original", None) is original_close


def test_pytest_runtime_installs_safe_multiprocessing_close():
    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close", False) is True


def test_main_suppresses_running_process_close_race_during_final_teardown(monkeypatch):
    monkeypatch.setattr(main_module, "MINIMAX_API_KEY", "test-key")
    monkeypatch.setattr(main_module, "_drain_active_children", lambda: None)

    class DummyPromptSession:
        def __init__(self, history=None):
            self.history = history

        def prompt(self, _message):
            raise EOFError

    class DummyDelirium:
        def generate_first_message(self):
            return ""

        def close(self):
            raise ValueError(RUNNING_PROCESS_CLOSE_ERROR)

    monkeypatch.setattr(main_module, "PromptSession", DummyPromptSession)
    monkeypatch.setattr(main_module, "Delirium", DummyDelirium)
    monkeypatch.setattr(main_module.console, "print", lambda *args, **kwargs: None)

    main_module.main()
