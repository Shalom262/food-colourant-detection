"""Read-only inference matching the BIN62 architecture walkthrough."""
import functools
import hashlib
import os
from pathlib import Path
import sys
import time
import types

import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn

from .model import ColourFusion, ResearchModel, class_probabilities, colour_representations

ROOT = Path(__file__).resolve().parents[2]
LABELS = ("Low", "Medium", "High")


def prepare_image(image):
    """EXIF transpose, whole-image RGB, square LANCZOS, no augmentation."""
    oriented = ImageOps.exif_transpose(image).convert("RGB")
    resized = oriented.resize((224, 224), Image.Resampling.LANCZOS)
    tensor = torch.from_numpy(np.array(resized, dtype=np.float32) / 255)
    return oriented, resized, tensor.permute(2, 0, 1).unsqueeze(0)


class Predictor:
    def __init__(self, device="cpu"):
        self.device = torch.device(device)
        checkpoint = ROOT / "outputs" / "best_csmon.pt"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Trained checkpoint missing: {checkpoint}")
        # This is the project's own trusted checkpoint, never an uploaded file.
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        if payload["class_mapping"] != dict(zip(LABELS, range(3))):
            raise ValueError("Checkpoint class mapping differs from Low / Medium / High.")
        arch, prep = payload["architecture"], payload["preprocessing"]
        if (arch["spec"]["kind"] != "vmamba" or arch["spec"]["fusion"] != "gated"
                or not arch["spec"]["ordinal"] or arch["fusion_channels"] != 12
                or prep["image_size"] != 224):
            raise ValueError("Unsupported checkpoint architecture or preprocessing.")
        provenance = payload["vmamba_provenance"]
        default = Path.home() / ".cache" / "csmon" / f"vmamba-{provenance['commit']}.py"
        source = Path(os.environ.get("CSMON_VMAMBA_SOURCE", str(default))).expanduser()
        if not source.is_file():
            raise FileNotFoundError(
                f"VMamba source missing: {source}. Use the notebook's WSL environment "
                "or set CSMON_VMAMBA_SOURCE to its cached source file. See demo/README.md."
            )
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != provenance["source_sha256"]:
            raise ValueError("VMamba source checksum does not match the trained checkpoint.")
        vmamba = types.ModuleType("csmon_demo_vmamba")
        vmamba.__file__ = str(source)
        sys.modules[vmamba.__name__] = vmamba
        exec(compile(data, str(source), "exec"), vmamba.__dict__)
        backbone = vmamba.VSSM(**arch["vmamba_kwargs"])
        backbone.classifier.head = nn.Identity()
        self.model = ResearchModel(backbone, 768, ColourFusion(12, True), True, True)
        self.model.load_state_dict(payload["state_dict"], strict=True)
        self.model.to(self.device).eval()
        # Same portable reference backend as the notebook, including on CUDA.
        for module in self.model.backbone.modules():
            if isinstance(module, vmamba.SS2D):
                module.forward_core = functools.partial(
                    module.forward_corev2, force_fp32=False, no_einsum=True,
                    selective_scan_backend="torch", scan_force_torch=True,
                )

    @torch.inference_mode()
    def predict(self, image):
        _, resized, x = prepare_image(image)
        x = x.to(self.device)
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()
        probabilities = class_probabilities(self.model(x))[0].cpu().numpy()
        gates = self.model.fusion.last_gates[0].cpu().numpy()
        elapsed = time.perf_counter() - start
        if not np.isfinite(probabilities).all() or (probabilities < 0).any():
            raise RuntimeError("Model returned invalid probabilities.")
        if not np.isclose(probabilities.sum(), 1, atol=1e-5):
            raise RuntimeError("Model probabilities do not sum to one.")
        predicted = int(probabilities.argmax())
        reps = colour_representations(x)
        # Display normalized channels as false-colour previews, not RGB conversions.
        previews = []
        for rep in reps:
            preview = ((rep[0].float().cpu().permute(1, 2, 0).numpy() + 1) / 2).clip(0, 1)
            previews.append(preview)
        return dict(label=LABELS[predicted], probabilities=probabilities,
                    gates=gates, seconds=elapsed, resized=resized, previews=previews)
