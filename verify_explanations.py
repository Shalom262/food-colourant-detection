"""Integration verification against real model weights and the exported forward fixture."""
import base64, io, json
from pathlib import Path
import numpy as np
from PIL import Image
import app

app.load_model()
assert app.state['status']=='ready', app.state
p=app.predictor
layer=p.model.backbone.model.layer[-1].norm1
initial_hooks=len(layer._forward_hooks)
module=__import__('sys').modules[type(p).__module__]
with np.load(app.BUNDLE/'fixtures'/'forward_inputs.npz',allow_pickle=False) as f:
    raw_p,raw_c=p.predict_tensors(module.torch.from_numpy(f['x']),module.torch.from_numpy(f['colour']))
expected=json.loads((app.BUNDLE/'fixtures'/'expected_forward.json').read_text())
assert np.allclose(raw_p.numpy(),expected['powder_logits'],atol=2e-4,rtol=2e-4)
assert np.allclose(raw_c.numpy(),expected['colouring_logits'],atol=2e-4,rtol=2e-4)
checks=[]
for sample in ['chilli','curry','turmeric']:
    path=app.ROOT/'static'/'samples'/f'{sample}.jpg'
    data=path.read_bytes()
    before=app.infer(data,path.name)
    explained=app.infer(data,path.name,True)
    after=app.infer(data,path.name)
    for name in ['raw_powder_probabilities','raw_colouring_probabilities']:
        assert before[name]==explained[name]==after[name], (sample,name)
    e=explained['explanations']
    assert e['patch_grid']==[14,14] and e['excluded_prefix_tokens']==5
    assert len(layer._forward_hooks)==initial_hooks
    assert not any(x.requires_grad or x.grad is not None for x in p.model.parameters())
    for task in ['powder','colouring']:
        cam=e['cams'][task]
        grid=np.asarray(cam['grid'])
        assert grid.shape==(14,14) and np.isfinite(grid).all()
        assert grid.min()>=0 and grid.max()<=1.000001
        assert cam['gradient_l1']>0
        assert cam['target']==explained[task]
        with Image.open(io.BytesIO(base64.b64decode(cam['map'].split(',')[1]))) as image:
            assert image.size==(384,384)
    assert not np.allclose(e['cams']['powder']['grid'],e['cams']['colouring']['grid']), 'Task CAMs unexpectedly identical'
    with Image.open(io.BytesIO(base64.b64decode(e['segmentation']['binary_mask'].split(',')[1]))) as image:
        assert set(np.unique(np.asarray(image))) <= {0,255}
    ig=e['colour_attribution']
    assert len(ig['features'])==54 and len(ig['groups'])==9
    assert ig['completeness_passed'], (sample,ig['completeness_residual'],ig['logit_difference'])
    assert abs(sum(g['attribution'] for g in ig['groups'])-ig['attribution_sum'])<1e-4
    check=dict(sample=sample,powder=explained['powder'],colouring=explained['colouring'],prediction_unchanged=True,patch_grid=e['patch_grid'],cams={k:dict(positive=v['has_positive_activation'],gradient_l1=v['gradient_l1']) for k,v in e['cams'].items()},ig_steps=ig['integration_steps'],ig_residual=ig['completeness_residual'],ig_difference=ig['logit_difference'],seconds=explained['elapsed_seconds'])
    checks.append(check)
    print(json.dumps(check),flush=True)
    if sample=='chilli':
        (app.ROOT/'preview'/'explanation_example.json').write_text(json.dumps(explained),encoding='utf-8')
record=dict(exported_forward_fixture='passed',frozen_weights_and_hook_cleanup='passed',checks=checks)
(app.ROOT/'explainability_verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('PASS: exported fixture, all 3 samples, prediction parity, CAM geometry, descriptor completeness, hook cleanup.',flush=True)
app.pool.shutdown()
