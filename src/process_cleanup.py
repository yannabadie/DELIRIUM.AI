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


def install_safe_multiprocessing_close() -> None:
    current_close = mp_process.BaseProcess.close
    if getattr(current_close, "_delirium_safe_close", False):
        return

    original_close = current_close

    def _patched_close(self):
        safe_close_process(self, original_close)

    _patched_close._delirium_safe_close = True
    _patched_close._delirium_safe_close_original = original_close
    mp_process.BaseProcess.close = _patched_close
