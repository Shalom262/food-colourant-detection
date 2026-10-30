# SpiceScope

A local web application for the trained DINOv3 seed-42 bundle.

## Open the app

1. Double-click **Start_SpiceScope.cmd**. This machine can use the existing Python runtime at D:\powder dataset\.venv.
2. Wait for the server startup message, then open http://127.0.0.1:8000 .
3. Wait until the page says **DINOv3 ready**. Select a real sample or upload an original JPG, PNG or WebP photo (up to 15 MB), then click **Analyze sample**.
4. Explore powder and colouring scores. Expand the processed region or download the JSON report.
5. The launcher now starts the server independently in the background. Closing the launcher window does not stop analysis. Run the launcher again to reconnect; it reuses a running server. Startup diagnostics are in server-output.log and server-error.log.

On another machine, install Python 3.11+, put this app beside the original bundle folder and run **Setup_SpiceScope.cmd** once (internet required). Then run **Start_SpiceScope.cmd**. To select another compatible runtime, set SPICE_PYTHON.

## What is included

- Responsive cream/forest-green interface; Three.js spice bowl with settling grains, drag and keyboard rotation, powder-linked illustrative colours, reduced-motion handling, offscreen pausing and a 2D fallback. The scene is decorative, not a model explanation.
- Drag-and-drop upload, local image preview, three real original dataset-frame samples, progress and actionable errors.
- Actual model predictions, raw probabilities for all three powder and five colouring categories, processed ROI preview and downloadable JSON.
- Test-evidence dialog reads the bundle CSV directly.
- Model initialization, checksum verification, strict weight loading and the original preprocessing stay in the exported bundle. App reads the bundle without editing it.
- Uploads are temporary and removed after analysis; inference runs locally. Only a supplementary Google Fonts stylesheet uses the internet; system fonts work offline.

To rebuild the bundled 3D assets after editing their source files, run `npm install` and `npm run build:3d`. The shared bundle keeps Node.js out of the app's runtime requirements.

## Model contract

Powders: Chilli, CurryPowder, Turmeric. Colourings: Pure, PillarRed, RosePink, LemonYellow, EggYellow. The exported model's independent argmax and all raw scores are preserved. The app applies a hard-coded powder-conditioned display policy: Chilli and CurryPowder allow Pure, PillarRed and RosePink; Turmeric allows Pure, LemonYellow and EggYellow. The final `colouring` output is selected from that powder's allowed classes; `model_colouring_prediction` and `raw_colouring_probabilities` retain the unfiltered model output. This does not invent a purity percentage or reuse results from another seed. Pure is a dataset category, not a chemical-purity measurement.

## Backend

GET /api/health, GET /api/info, GET /api/samples, POST /api/predict (multipart file). SPICE_BUNDLE_PATH overrides bundle discovery; SPICE_DEVICE defaults to cpu; SPICE_PORT defaults to 8000. The server binds to 127.0.0.1. CPU inference is serialized and uses four Torch threads. No trained weights are copied into the web assets.


## Explain this prediction

After Analyze sample, use Generate explanations in the Why this prediction? panel.

- Separate powder and colouring Grad-CAM overlays use block 12 pre-attention LayerNorm. The 14x14 patch grid excludes CLS and all four register tokens. Each map is normalized independently; compare patterns rather than absolute strengths. Change overlay opacity or download either composite PNG.
- The mask panel shows the original analysis-size image, binary preprocessing mask, detected contour and prepared image. This is a heuristic region mask, not a dye annotation. A failed ROI check is disclosed and follows the original full-image fallback.
- Colour feature contributions use Integrated Gradients of the predicted colouring logit. The image embedding is held fixed and all 54 descriptor features interpolate from an all-zero artificial reference to their actual values. This baseline is not a Pure powder reference. The chart displays signed groups; expand the table for all feature values and contributions. Positive/negative means supporting/opposing the target relative to that baseline, not a probability or a measured dye quantity.
- Gaussian quadrature uses 64 steps, increasing to 128 or 256 if the completeness residual exceeds max(0.01 logit units, 1% of the endpoint logit difference). The residual and approximation status are displayed.
- Heatmaps do not locate dye or measure its concentration. The colouring heatmap covers the visual branch only; descriptor contributions are shown separately.
- The JSON report includes patch grids, targets, all 54 contributions, baseline/method metadata and completeness checks. Image data is excluded; download overlay PNGs separately.

POST /api/explain accepts the same file upload as /api/predict. Explanations are calculated on demand and use the same serialized model worker. No additional Python dependency is required. Trained weights remain frozen and unchanged. Forward hooks are removed after every explanation, including on errors.

Run verify_explanations.py with the app runtime for the exported forward fixture, real samples from all three powders, prediction invariance before/after attribution, nonzero gradients, token-grid geometry, binary mask validity, IG completeness and hook cleanup. The results are in explainability_verification.json.


## Connection recovery

If an old open page says Failed to fetch, double-click Start_SpiceScope.cmd and reopen http://127.0.0.1:8000. The page now checks the connection every five seconds and gives launcher instructions when disconnected. The launcher starts the server in the background and waits for model readiness before opening the page. Run python launch.py --no-browser to verify startup without opening a browser.
