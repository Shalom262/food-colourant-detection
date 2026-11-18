"""Focused integration checks; never writes model or dataset artifacts."""
import sys
sys.dont_write_bytecode = True

import json
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch
from streamlit.testing.v1 import AppTest

from inference.predictor import ROOT, Predictor, prepare_image
from inference.model import class_probabilities


def main():
    # Verify EXIF orientation and the exact whole-image tensor transformation.
    image = Image.new("RGB", (19, 31), (210, 55, 12))
    exif = image.getexif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    buffer.seek(0)
    with Image.open(buffer) as oriented:
        full, small, x = prepare_image(oriented)
        assert full.size == (31, 19)
        expected = ImageOps.exif_transpose(oriented).convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
        np.testing.assert_array_equal(np.array(small), np.array(expected))
        np.testing.assert_allclose(x[0].permute(1, 2, 0).numpy(), np.array(expected, dtype=np.float32) / 255)
    p = class_probabilities(torch.tensor([[-1., -3.], [3., 1.]]))
    assert (p >= 0).all()
    torch.testing.assert_close(p.sum(1), torch.ones(2))
    print("PASS: EXIF orientation, resize, scaling, ordinal probabilities")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(4)
    predictor = Predictor(device)
    sample = ROOT / "Dataset" / "BIN62.jpg"
    with Image.open(sample) as opened:
        result = predictor.predict(opened)
        _, _, tensor = prepare_image(opened)
    # Reconstruct the notebook model classes independently and share the exact
    # backbone; this catches drift in the extracted fusion, head, and wrapper.
    notebook = json.loads((ROOT / "03_csmon_architecture_BIN62.ipynb").read_text())
    namespace = {}
    exec("import math\nimport torch\nfrom torch import nn\nfrom torch.nn import functional as F\nimport kornia.color as colour", namespace)
    cell = next(c for c in notebook["cells"] if c["cell_type"] == "code"
                and "class ResearchModel" in "".join(c["source"]))
    exec("".join(cell["source"]), namespace)
    baseline = namespace["ResearchModel"](predictor.model.backbone, 768,
                                         namespace["ColourFusion"](12, True), True, True)
    baseline.load_state_dict(predictor.model.state_dict(), strict=True)
    baseline.to(device).eval()
    with torch.inference_mode():
        expected = namespace["class_probabilities"](baseline(tensor.to(device)))[0].cpu().numpy()
    np.testing.assert_allclose(result["probabilities"], expected, rtol=1e-5, atol=1e-6)
    assert np.isclose(result["gates"].sum(), 1)
    print("PASS: checkpoint inference matches notebook", result["label"], result["probabilities"])
    del baseline, predictor
    if device == "cuda":
        torch.cuda.empty_cache()

    app = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=180).run()
    assert not app.exception, app.exception
    assert app.button[0].disabled
    app.radio[0].set_value("Test examples").run()
    assert not app.exception, app.exception
    assert not app.button[0].disabled
    app.button[0].click().run()
    assert not app.exception, app.exception
    assert not app.error, app.error
    assert len(app.metric) == 2
    assert app.metric[0].value in ("Low", "Medium", "High")
    app.radio[0].set_value("Upload").run()
    assert not app.metric, "Previous prediction remained after changing input"
    print("PASS: UI empty state, held-out example inference, stale result clearing")


if __name__ == "__main__":
    main()
