# CS-MON presentation demo

A local Streamlit interface for the existing `../outputs/best_csmon.pt` checkpoint.
All demo code and its optional environment live here. The checkpoint, dataset,
notebooks, and root environment are read-only; uploaded photographs stay in memory.

## Launch on this machine

From PowerShell in the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\demo\run.ps1
```

Open **http://localhost:8501** in your Windows browser. Keep the terminal open;
press Ctrl+C to stop. The launcher uses the Ubuntu-22.04 WSL distribution.

## Environment setup (first time or after removing demo/.venv)

In WSL, navigate to the project root, then run:

```bash
/home/csmon/.venvs/csmon-gpu/bin/python demo/setup_env.py
cd demo
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

This reuses the working notebook environment's model packages without changing it.
The setup script adds a path reference to its packages inside `demo/.venv`.
For a different machine, create a Python 3.10+ virtual environment in this folder,
install `requirements.txt`, and provide the exact cached VMamba source described below.
Use a PyTorch/torchvision combination appropriate for that machine's CPU or CUDA.

## VMamba source

The loader uses the same source as the architecture walkthrough:
`~/.cache/csmon/vmamba-<checkpoint commit>.py`. It validates its SHA-256 against
the checkpoint before executing the source and strictly loads the state dict.
The checkpoint itself must remain the trusted project checkpoint.

If the cache is elsewhere, set `CSMON_VMAMBA_SOURCE` to that file before launch.
On another machine, copy this cached source from the notebook environment;
the demo does not download or replace it automatically. A missing checkpoint or
source produces a visible error rather than a simulated prediction.

## Demo flow

1. Upload a JPG/PNG/WebP, capture a camera photograph, or choose a held-out test example.
2. Select **Analyse image**. The first run includes model loading.
3. Present the intensity estimate and the three class probabilities.
4. Expand the colour-space panel to show the input and adaptive fusion weights.

CPU and CUDA use the notebook's PyTorch reference scan backend. CPU inference can
be slow. Probabilities are not calibrated confidence; fusion weights are not
chemical measurements. The sweet type is not predicted. Test examples use the
manifest's split and hashes; their original label provenance is shown alongside
the recorded label. A selected example does not establish overall performance.

The result describes predefined intensity categories. It does not identify dyes,
measure concentrations, or certify food safety.

## Checks

From this folder in WSL:

```bash
.venv/bin/python verify.py
```

This checks the preprocessing and ordinal probabilities, then compares a real
checkpoint prediction against the model classes extracted independently from the
architecture notebook. It runs a Streamlit AppTest of the upload landing page and
an example prediction, without writing results or changing research files.
