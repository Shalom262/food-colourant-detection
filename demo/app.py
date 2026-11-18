"""Launch with: python -m streamlit run app.py (from demo/)."""
import utils.net
import utils.clients
import utils.http_session
import utils.transport
import utils.session
import sys
sys.dont_write_bytecode = True

from io import BytesIO
import hashlib
from pathlib import Path
import threading

import pandas as pd
from PIL import Image, UnidentifiedImageError
import streamlit as st
import torch

from inference.predictor import LABELS, ROOT, Predictor, prepare_image

st.set_page_config(page_title="CS-MON | Colour Intensity Demo", page_icon="🍬", layout="wide")
st.markdown("""
<style>
.stApp { background: #f7f8fa; }
.block-container { max-width: 1200px; padding-top: 2.5rem; }
h1, h2, h3 { color: #183d39; }
.eyebrow { color: #54716d; letter-spacing: .16em; font-size: .78rem; font-weight: 700; }
.intro { color: #596b70; max-width: 760px; font-size: 1.05rem; }
div[data-testid="stMetric"] { background: white; border: 1px solid #dce5e3;
border-radius: 12px; padding: 18px; }
div.stButton > button[kind="primary"] { background: #146b5b; border-color: #146b5b; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_predictor(device):
    return Predictor(device), threading.Lock()


@st.cache_data
def test_examples():
    manifest = ROOT / "outputs" / "split_manifest.csv"
    if not manifest.is_file():
        return pd.DataFrame()
    table = pd.read_csv(manifest).fillna("")
    table = table.loc[table["split"].eq("test")]
    # Deterministic selection across sweet types and intensity labels.
    return table.sort_values("image_id").groupby(
        ["sweet", "colouring_intensity"], sort=True
    ).head(2).reset_index(drop=True)


st.markdown('<p class="eyebrow">CS-MON · RESEARCH DEMONSTRATOR</p>', unsafe_allow_html=True)
st.title("Explore colour intensity in sweets")
st.markdown('<p class="intro">Upload a photograph of Kesari, Muscat, or Boondhi to '
            'estimate its colour intensity with the trained Colour-Space Mamba-Ordinal Network.</p>',
            unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Demo settings")
    devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    device = st.selectbox("Inference device", devices, index=len(devices) - 1,
                          format_func=lambda d: "GPU (CUDA)" if d == "cuda" else "CPU")
    st.caption("The model loads once per device. The first prediction can take longer.")
    st.divider()
    st.markdown("**Model workflow**")
    st.markdown("Image → RGB / HSV / Lab → adaptive fusion → VMamba → ordinal prediction")
    st.caption("Three ordered categories: Low < Medium < High.")
    st.caption("The model estimates intensity; it does not classify the sweet type.")

left, right = st.columns([1.05, 1], gap="large")
with left:
    st.subheader("1. Choose an image")
    source = st.radio("Image source", ["Upload", "Camera", "Test examples"], horizontal=True)
    raw, example = None, None
    if source == "Upload":
        uploaded = st.file_uploader("Upload a JPG, PNG, or WebP", type=["jpg", "jpeg", "png", "webp"])
        if uploaded is not None:
            raw = uploaded.getvalue()
    elif source == "Camera":
        captured = st.camera_input("Photograph your sweet")
        if captured is not None:
            raw = captured.getvalue()
    else:
        examples = test_examples()
        if examples.empty:
            st.info("No held-out examples found in the split manifest. Upload an image instead.")
        else:
            index = st.selectbox("Held-out test image", range(len(examples)),
                                 format_func=lambda i: f"{examples.iloc[i]['image_id']} · {examples.iloc[i]['sweet']}")
            example = examples.iloc[index]
            path = (ROOT / example["relative_path"]).resolve()
            if path.is_relative_to((ROOT / "Dataset").resolve()) and path.is_file():
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != example["sha256"]:
                    st.error("This example differs from the image recorded in the manifest.")
                    raw = None
            else:
                st.error("Example image is unavailable. Upload a photograph instead.")
            st.caption("Examples come from the recorded test split. One example is not an accuracy evaluation.")

    image = None
    if raw:
        try:
            if len(raw) > 20 * 1024 * 1024:
                raise ValueError("Please choose an image smaller than 20 MB.")
            with Image.open(BytesIO(raw)) as opened:
                image, _, _ = prepare_image(opened)
            st.image(image, caption="Input photograph", width="stretch")
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            st.error(f"Cannot read this image: {exc}")

    analyse = st.button("Analyse image", type="primary", disabled=image is None,
                        width="stretch")

key = hashlib.sha256(raw).hexdigest() + device if raw else None
if st.session_state.get("result_key") != key:
    st.session_state.pop("result", None)
if analyse and image is not None:
    try:
        with st.spinner("Loading CS-MON and analysing the photograph…"):
            predictor, lock = load_predictor(device)
            with lock:
                result = predictor.predict(image)
            st.session_state.update(result=result, result_key=key)
    except Exception as exc:
        st.error(f"Prediction could not run: {exc}")
        st.caption("Check the setup instructions in demo/README.md. No prediction has been generated.")

with right:
    st.subheader("2. View the estimate")
    result = st.session_state.get("result")
    if result is None:
        st.info("Choose a photograph, then select Analyse image to see the model’s estimate.")
        st.markdown("**What you will see**")
        st.write("An intensity category, class probabilities, and the relative colour-space fusion weights.")
    else:
        a, b = st.columns(2)
        a.metric("Estimated intensity", result["label"])
        b.metric("Model probability", f"{max(result['probabilities']):.1%}")
        st.caption(f"Model inference: {result['seconds']:.2f} s · {device.upper()}")
        chart = pd.DataFrame({"Intensity": LABELS, "Probability": result["probabilities"]})
        st.bar_chart(chart, x="Intensity", y="Probability", color="#146b5b", sort=False)
        st.caption("Model probabilities are not calibrated certainty or dye concentrations.")
        if example is not None:
            st.write(f"Recorded dataset label: **{example['colouring_intensity']}**")
            st.caption("Dataset label provenance: " + str(example.get("label_provenance", "Not recorded")))
        with st.expander("Explore the colour-space fusion"):
            st.image(result["resized"], caption="Model input · 224 × 224 pixels", width=224)
            panels = st.columns(3)
            for panel, name, preview, weight in zip(panels, ["RGB", "HSV", "Lab"], result["previews"], result["gates"]):
                panel.image(preview, caption=f"{name} · {weight:.1%}", width="stretch")
            st.caption("HSV and Lab panels show normalized channels as false colours. "
                       "Weights describe how the fusion combines colour-space features; "
                       "they are not region-level explanations or evidence of chemical content.")

st.divider()
st.caption("Research demo · Estimates predefined colour-intensity categories from images. "
           "Does not identify chemical colourants, measure dye concentration, or certify food safety.")
