import logging
import os
import subprocess


LOGGER = logging.getLogger(__name__)


def compile_scad_to_stl(scad_code: str, output_path: str = "outputs/turret.stl") -> str:
    """
    Write OpenSCAD code to a .scad file and compile to STL when OpenSCAD is installed.
    Returns the absolute STL path on success, otherwise an empty string.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    scad_path = output_path.replace(".stl", ".scad")
    with open(scad_path, "w", encoding="utf-8") as file:
        file.write(scad_code)

    try:
        result = subprocess.run(
            ["openscad", "-o", output_path, scad_path],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError:
        LOGGER.warning("OpenSCAD CLI not found. Wrote %s but skipped STL compilation.", scad_path)
        return ""

    if result.returncode != 0:
        raise RuntimeError(f"OpenSCAD compilation failed:\n{result.stderr}")

    return os.path.abspath(output_path)
