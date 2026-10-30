"""Class-targeted explanations for the unchanged frozen two-head DINOv3 model.

CAMs target block 12 norm1; CLS and register tokens are excluded from the spatial
map. Descriptor IG holds the visual embedding fixed, with a documented zero
54-D descriptor baseline. Neither method estimates dye location/concentration.
"""
from __future__ import annotations
import base64
import io
import time
import numpy as np
import cv2
import torch
from PIL import Image


def png_data(rgb):
    stream = io.BytesIO()
    Image.fromarray(np.asarray(rgb, dtype=np.uint8)).save(stream, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')


def class_cam(activation, gradient, prefix, side):
    if activation.shape[1] != prefix + side * side:
        raise ValueError('Unexpected transformer token layout for Grad-CAM.')
    features = activation[0, prefix:, :].detach().float()
    gradients = gradient[0, prefix:, :].detach().float()
    weights = gradients.mean(dim=0)
    raw = (features * weights).sum(dim=-1).reshape(side, side).relu()
    if not torch.isfinite(raw).all():
        raise FloatingPointError('Non-finite Grad-CAM values.')
    peak = float(raw.max())
    positive = peak > 1e-12
    normalized = (raw / peak).cpu().numpy() if positive else np.zeros((side, side), np.float32)
    return normalized, positive, peak


def descriptor_ig(model, embedding, descriptor, target, *, tolerance=.01):
    """Gauss-Legendre IG of target colouring logit; visual features held fixed."""
    actual = descriptor.detach()
    baseline = torch.zeros_like(actual)
    fixed = embedding.detach()
    def score(values):
        visual = fixed.expand(values.shape[0], -1)
        return model.colouring_head(torch.cat([visual, model.colour_encoder(values)], dim=1))[:, target]
    with torch.no_grad():
        end_score = float(score(actual)[0])
        start_score = float(score(baseline)[0])
    delta = end_score - start_score
    for steps in (64, 128, 256):
        nodes, weights = np.polynomial.legendre.leggauss(steps)
        alpha = torch.as_tensor((nodes + 1) / 2, device=actual.device, dtype=actual.dtype)[:, None]
        weights = torch.as_tensor(weights / 2, device=actual.device, dtype=actual.dtype)[:, None]
        path = (baseline + alpha * (actual - baseline)).requires_grad_(True)
        with torch.enable_grad():
            values = score(path)
            gradients = torch.autograd.grad(values.sum(), path)[0]
        attrs = ((actual - baseline) * (gradients * weights).sum(dim=0, keepdim=True))[0]
        residual = float(attrs.sum()) - delta
        if abs(residual) <= max(.01, tolerance * abs(delta)):
            break
    if not torch.isfinite(attrs).all():
        raise FloatingPointError('Non-finite descriptor attribution.')
    values = attrs.detach().cpu().numpy()
    labels = ['L* mean', 'a* mean', 'b* mean', 'L* spread', 'a* spread', 'b* spread']
    labels += [f'{channel} histogram bin {i+1}/16' for channel in ['Hue','Saturation','Value'] for i in range(16)]
    features = [dict(name=name, value=float(actual[0,i]), attribution=float(values[i])) for i,name in enumerate(labels)]
    groups = [dict(name=labels[i], attribution=float(values[i]), absolute_contribution=float(abs(values[i]))) for i in range(6)]
    for name,start in [('Hue histogram',6),('Saturation histogram',22),('Value histogram',38)]:
        groups.append(dict(name=name, attribution=float(values[start:start+16].sum()), absolute_contribution=float(abs(values[start:start+16]).sum())))
    return dict(method='Integrated Gradients (Gauss-Legendre)', baseline='All-zero 54-dimensional descriptor; an artificial reference, not a Pure sample.', scope='Colouring head only. Visual embedding held fixed. Contributions are to the predicted class logit, not percentages.', target_logit=end_score, baseline_logit=start_score, logit_difference=delta, attribution_sum=float(values.sum()), completeness_residual=residual, integration_steps=steps, completeness_passed=abs(residual)<=max(.01,tolerance*abs(delta)), groups=groups, features=features)


def explain_prepared(predictor, rgb, diagnostic, result):
    started = time.perf_counter()
    # Use the exact exported descriptor and tensor transformation.
    import sys
    module = sys.modules[type(predictor).__module__]
    descriptor, _ = module.colour_descriptor(rgb, predictor.preprocess)
    image = module.image_tensor(rgb, CFG=predictor.tensor_config, MEAN=predictor.mean, STD=predictor.std)[None].to(predictor.device)
    colour = torch.from_numpy(descriptor)[None].to(predictor.device)
    powder_target = predictor.powders.index(result['powder'])
    colouring_target = predictor.colourings.index(result['colouring'])
    model = predictor.model
    target_layer = model.backbone.model.layer[-1].norm1
    captured = {}
    def capture(_layer, _inputs, output):
        # Frozen upstream weights need no graph. Re-enable gradients at the target
        # activation only; this preserves the forward values and avoids retraining.
        output = output.requires_grad_(True)
        captured['activation'] = output
        return output
    handle = target_layer.register_forward_hook(capture)
    try:
        with torch.enable_grad():
            powder_logits, colouring_logits, embedding = model(image, colour)
            activation = captured['activation']
            powder_gradient = torch.autograd.grad(powder_logits[0,powder_target], activation, retain_graph=True)[0]
            colouring_gradient = torch.autograd.grad(colouring_logits[0,colouring_target], activation)[0]
        if not np.allclose(powder_logits.detach().softmax(1).cpu().numpy()[0], list(result['raw_powder_probabilities'].values()), atol=2e-5, rtol=2e-5):
            raise RuntimeError('Explanation forward differs from prediction.')
        if not np.allclose(colouring_logits.detach().softmax(1).cpu().numpy()[0], list(result['raw_colouring_probabilities'].values()), atol=2e-5, rtol=2e-5):
            raise RuntimeError('Explanation forward differs from prediction.')
        prefix = 1 + int(model.backbone.config.num_register_tokens)
        patch = model.backbone.config.patch_size
        if not isinstance(patch,int): patch=patch[0]
        side = image.shape[-1] // patch
        cams = {}
        for task,target,gradient in [('powder',result['powder'],powder_gradient),('colouring',result['colouring'],colouring_gradient)]:
            grid, positive, peak = class_cam(activation, gradient, prefix, side)
            smooth = cv2.resize(grid, (rgb.shape[1],rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
            heat = cv2.cvtColor(cv2.applyColorMap(np.uint8(np.clip(smooth,0,1)*255), cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
            cams[task] = dict(target=target, map=png_data(heat), grid=grid.tolist(), has_positive_activation=positive, raw_positive_peak=peak, gradient_l1=float(gradient[:,prefix:,:].abs().sum()), note='Positive class-specific visual attribution; independently normalized. Colour descriptor is held fixed.' if positive else 'No positive Grad-CAM activation at this layer for this target. No heatmap should be interpreted.')
        attribution = descriptor_ig(model, embedding, colour, colouring_target)
    finally:
        handle.remove()
        captured.clear()
    raw = diagnostic['raw']
    mask = diagnostic['mask'].astype(np.uint8)*255
    contour = raw.copy()
    contours,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(contour, contours, -1, (30,140,85), 2)
    return dict(method='Grad-CAM', layer='backbone.model.layer.11.norm1 (transformer block 12, pre-attention LayerNorm)', patch_grid=[side,side], excluded_prefix_tokens=prefix, prepared_image=png_data(rgb), cams=cams, segmentation=dict(original=png_data(raw), binary_mask=png_data(mask), contour=png_data(contour), prepared=png_data(rgb), coverage=float((mask>0).mean()), roi_valid=bool(result['preprocessing']['roi_valid']), note='Heuristic preprocessing mask, not a chemical annotation or dye segmentation.'), colour_attribution=attribution, elapsed_seconds=round(time.perf_counter()-started,3), note='Attribution explains model behavior; it does not locate dye or measure concentration. The two CAMs use separate relative scales.')
