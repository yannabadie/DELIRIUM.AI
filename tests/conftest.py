import tempfile
from pathlib import Path

from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir


# Keep local property-test runs deterministic and free of repo cache artifacts.
set_hypothesis_home_dir(Path(tempfile.gettempdir()) / "coral-persona-hypothesis")
settings.register_profile("repo_clean", settings(database=None))
settings.load_profile("repo_clean")
