"""Local web interface around the unchanged exported DINOv3 bundle."""
from __future__ import annotations
import asyncio, base64, csv, importlib.util, io, json, logging, os, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
BUNDLE = Path(os.environ.get('SPICE_BUNDLE_PATH', str(ROOT.parent / 'dinov3_standard_seed42_9061fbac4697_WebApp_Bundle' / 'dinov3_standard_seed42_9061fbac4697')))
META = json.loads((BUNDLE / 'model_metadata.json').read_text(encoding='utf-8'))
MAX_BYTES = 15 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 25_000_000
pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='spicescope')
state = {'status': 'loading', 'message': 'Loading trained DINOv3 weights...'}
predictor = None
log = logging.getLogger('spicescope')

def load_model():
    global predictor
    try:
        spec = importlib.util.spec_from_file_location('spicescope_bundle_inference', BUNDLE / 'inference.py')
        import torch
        torch.set_num_threads(4)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        predictor = module.PowderPredictor(BUNDLE, device=os.environ.get('SPICE_DEVICE', 'cpu'))
        state.update(status='ready', message='Trained model ready', device=str(predictor.device))
    except Exception as exc:
        log.exception('Model initialization failed')
        state.update(status='unavailable', message='Model runtime needs setup. Run Setup_SpiceScope.cmd, then restart.', detail=str(exc))

@asynccontextmanager
async def lifespan(app):
    task = asyncio.get_running_loop().run_in_executor(pool, load_model)
    yield
    await task
    pool.shutdown(wait=True)

app = FastAPI(title='SpiceScope', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/health')
def health():
    return dict(state)

@app.get('/api/info')
def info():
    metrics = []
    evidence = BUNDLE / 'evaluation_evidence' / 'all_raw_metrics.csv'
    if evidence.is_file():
        with evidence.open(newline='', encoding='utf-8') as handle:
            metrics = [row for row in csv.DictReader(handle) if row['split'] == 'test']
    return {'model': 'DINOv3 ViT-B/16', 'seed': META['seed'], 'powders': META['powders'], 'colourings': META['colourings'], 'image_size': META['image_size'], 'test_evidence': metrics, 'policy': META['prediction_policy']}

@app.get('/api/samples')
def samples():
    path = ROOT / 'static' / 'samples' / 'manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []

def encode_preview(image):
    out = io.BytesIO()
    image.thumbnail((640,640))
    image.save(out, format='JPEG', quality=85)
    return 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode('ascii')

def infer(data, filename, with_explanations=False):
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='spicescope-') as directory:
        path = Path(directory) / ('upload' + (Path(filename).suffix.lower() or '.jpg'))
        path.write_bytes(data)
        rgb, preparation, diagnostic = predictor.preprocess.prepare_path(path, size=predictor.metadata['preprocessing_export_size'], mode=predictor.metadata['input_mode'], analysis_side=predictor.metadata['analysis_side'])
        preparation = sys.modules[type(predictor).__module__]._json_safe(preparation)
        result = predictor.predict_prepared(rgb)
        result['preprocessing'] = preparation
        if with_explanations:
            from explainability import explain_prepared
            result['explanations'] = explain_prepared(predictor, rgb, diagnostic, result)
        result.update(preprocessing=preparation, prepared_preview=encode_preview(Image.fromarray(rgb)), elapsed_seconds=round(time.perf_counter()-start,3), filename=Path(filename).name, model='DINOv3 ViT-B/16 - seed 42')
        return result

async def process_upload(file, with_explanations=False):
    if state['status'] != 'ready':
        raise HTTPException(503, state['message'])
    data = await file.read(MAX_BYTES+1)
    await file.close()
    if not data: raise HTTPException(400, 'Choose a photo first.')
    if len(data)>MAX_BYTES: raise HTTPException(413, 'Please use a photo under 15 MB.')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {'JPEG','PNG','WEBP'}: raise HTTPException(415, 'Please use a JPG, PNG or WebP photo.')
            image.verify()
    except HTTPException: raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, 'This image cannot be read. Please choose a smaller, valid photo.')
    try:
        return await asyncio.get_running_loop().run_in_executor(pool, infer, data, file.filename or 'photo.jpg', with_explanations)
    except ValueError:
        raise HTTPException(422, 'A reliable powder region could not be detected. Try a clear powder photo on a plain white background.')
    except Exception:
        log.exception('Inference failed')
        raise HTTPException(500, 'Analysis could not finish. Please try another clear powder photo.')

@app.post('/api/predict')
async def predict(file: UploadFile = File(...)):
    return await process_upload(file)

@app.post('/api/explain')
async def explain(file: UploadFile = File(...)):
    return await process_upload(file, with_explanations=True)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('SPICE_PORT','8000')))
