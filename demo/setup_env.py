"""Run with the working notebook Python to create an isolated demo environment."""
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import venv


def main():
    folder = Path(__file__).resolve().parent
    target = folder / ".venv"
    if Path(sys.prefix).resolve() == target.resolve():
        raise SystemExit("Run this script using the notebook's Python, not demo/.venv.")
    # Model packages stay in the notebook environment; UI additions live here.
    venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(target)
    executable = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    purelib = subprocess.check_output(
        [str(executable), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True
    ).strip()
    Path(purelib, "csmon-notebook.pth").write_text(sysconfig.get_path("purelib") + "\n")
    subprocess.run([str(executable), "-m", "pip", "install", "-r",
                    str(folder / "requirements-ui.txt")], check=True)
    print("Ready. From demo/: .venv/bin/python -m streamlit run app.py")


if __name__ == "__main__":
    main()
