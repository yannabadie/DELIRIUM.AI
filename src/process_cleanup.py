import atexit
import multiprocessing
import multiprocessing.process as mp_process


RUNNING_PROCESS_CLOSE_ERROR = "Cannot close a process while it is still running."


def is_running_process_close_error(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and RUNNING_PROCESS_CLOSE_ERROR in str(exc)


def _process_is_running(process) -> bool:
    popen = getattr(process, "_popen", None)
    if popen is not None:
        try:
            return popen.poll() is None
        except Exception:
            pass

    is_alive = getattr(process, "is_alive", None)
    if callable(is_alive):
        try:
            return bool(is_alive())
        except Exception:
            pass

    return False


def safe_close_process(process, original_close, join_timeout: float = 0.2, terminate_timeout: float = 1.0) -> bool:
    try:
        original_close(process)
        return True
    except ValueError as exc:
        if not is_running_process_close_error(exc):
            raise

    join = getattr(process, "join", None)
    if callable(join):
        try:
            join(timeout=join_timeout)
        except Exception:
            pass

    if _process_is_running(process):
        terminate = getattr(process, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except Exception:
                pass
        if callable(join):
            try:
                join(timeout=terminate_timeout)
            except Exception:
                pass

    if _process_is_running(process):
        return False

    try:
        original_close(process)
        return True
    except ValueError as exc:
        if is_running_process_close_error(exc):
            return False
        raise


def drain_active_children(join_timeout: float = 0.2, terminate_timeout: float = 1.0) -> None:
    """Best-effort cleanup for multiprocessing children left by dependencies."""
    original_close = getattr(mp_process.BaseProcess.close, "_delirium_safe_close_original", mp_process.BaseProcess.close)

    for child in multiprocessing.active_children():
        try:
            safe_close_process(
                child,
                original_close,
                join_timeout=join_timeout,
                terminate_timeout=terminate_timeout,
            )
        except Exception:
            continue


def install_process_cleanup_atexit() -> None:
    if getattr(install_process_cleanup_atexit, "_delirium_registered", False):
        return

    atexit.register(drain_active_children)
    install_process_cleanup_atexit._delirium_registered = True


def install_safe_multiprocessing_close() -> None:
    current_close = mp_process.BaseProcess.close
    if getattr(current_close, "_delirium_safe_close_source", None) == "product":
        install_process_cleanup_atexit()
        return

    original_close = current_close

    def _patched_close(self):
        safe_close_process(self, original_close)

    _patched_close._delirium_safe_close = True
    _patched_close._delirium_safe_close_source = "product"
    _patched_close._delirium_safe_close_original = original_close
    mp_process.BaseProcess.close = _patched_close
    install_process_cleanup_atexit()
