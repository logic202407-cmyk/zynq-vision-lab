"""Run the preserved camera geometry tests in the repository's normal suite."""
import importlib.util
from pathlib import Path


def load_tests(loader, tests, pattern):
    path = (Path(__file__).resolve().parents[1] /
            "src/prototype/skystar_openmv/three_cameras/tests/test_geometry.py")
    spec = importlib.util.spec_from_file_location("three_camera_geometry_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromTestCase(module.GeometryTests)
