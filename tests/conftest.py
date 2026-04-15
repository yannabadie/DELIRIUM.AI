import tempfile
from pathlib import Path

from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir

from src.process_cleanup import install_safe_multiprocessing_close


# Keep local property-test runs deterministic and free of repo cache artifacts.
set_hypothesis_home_dir(Path(tempfile.gettempdir()) / "coral-persona-hypothesis")
settings.register_profile("repo_clean", settings(database=None))
settings.load_profile("repo_clean")

# Pytest always imports this file in the grader runtime, unlike repo-root
# sitecustomize.py which is shadowed by the system interpreter's startup hook.
install_safe_multiprocessing_close()
