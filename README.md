# CS-MON: Colour-Space Mamba-Ordinal Network

### Explainable Artificial Colour Intensity Estimation in Traditional Sri Lankan Sweets

CS-MON (Colour-Space Mamba-Ordinal Network) is a computer vision research approach designed to estimate artificial-colour intensity levels in traditional Sri Lankan sweets using smartphone-captured images.

The system combines adaptive multi-colour-space feature learning, a fine-tuned VMamba-Tiny backbone, and ordinal learning to classify food samples into three ordered intensity categories: **Low, Medium, and High**.

This research aims to investigate an accessible, non-destructive method for preliminary artificial-colour intensity screening without relying on specialized laboratory imaging equipment.

---

## 1. Research Overview

Artificial food colourants are commonly used to enhance the visual appearance of sweets. However, differences in colourant intensity can be difficult to assess consistently through visual observation, particularly under varying lighting conditions, camera settings, and food preparation characteristics.

Traditional laboratory-based analytical methods can provide information about food colourants but often require specialized instruments, sample preparation, and trained personnel.

This research explores the potential of smartphone-based computer vision to estimate predefined artificial-colour intensity categories directly from food images.

The study focuses on three traditional sweets:

- **Kesari**
- **Muscat**
- **Boondhi**

The proposed system predicts one of three ordered intensity levels:

| Class | Label | Description |
|---|---|---|
| Low | 0 | Low artificial-colour intensity |
| Medium | 1 | Moderate artificial-colour intensity |
| High | 2 | High artificial-colour intensity |

The intensity categories are intended to be defined using documented preparation information or suitable reference measurements rather than image appearance alone.

## 2. Research Problem

Smartphone photographs contain useful colour information, but their appearance can be influenced by illumination, camera processing, background conditions, and food texture.

Conventional image classification models may not explicitly utilize complementary colour representations or account for the natural ordering between intensity levels.

Therefore, the research investigates the following question:

**How can adaptive colour-space learning, visual state-space modelling, and ordinal classification be combined to estimate artificial-colour intensity levels in traditional sweets using smartphone images?**

## 3. Proposed Approach

The proposed **CS-MON architecture** integrates three principal components.

### Adaptive Colour-Space Fusion

Each input image is represented in three colour spaces:

- **RGB:** Preserves the original colour information.
- **HSV:** Represents hue, saturation, and brightness characteristics.
- **CIELAB:** Represents perceptual lightness and chromatic characteristics.

Separate learnable projection modules extract features from each colour representation.

A sample-dependent gating mechanism learns the relative contribution of RGB, HSV, and CIELAB features and combines them into a unified representation.

### Fine-Tuned VMamba-Tiny

The fused colour representation is passed into a pretrained VMamba-Tiny visual state-space backbone.

VMamba uses hierarchical feature extraction and selective state-space operations to capture local visual patterns and broader spatial relationships.

The pretrained backbone is fine-tuned on the traditional-sweets image dataset to adapt its feature representations to the specific intensity estimation task.

### CORAL Ordinal Learning

Instead of treating Low, Medium, and High as unrelated classes, the proposed model uses a CORAL-style ordinal prediction head.

The ordinal head learns cumulative intensity thresholds while preserving the ordering:

**Low < Medium < High**

This formulation is intended to support more appropriate handling of prediction errors between ordered intensity categories.

## 4. Proposed System Architecture

The overall prediction pipeline is:

```text
Smartphone Food Image
          |
          v
Colour-Preserving Preprocessing
          |
          v
RGB / HSV / CIELAB Representations
          |
          v
Learnable Colour-Space Projections
          |
          v
Sample-Dependent Adaptive Fusion
          |
          v
3-Channel Fusion Adapter
     + RGB Residual
          |
          v
Fine-Tuned VMamba-Tiny
          |
          v
Hierarchical Visual Features
          |
          v
Global Feature Pooling
          |
          v
CORAL Ordinal Prediction Head
          |
          v
  Low / Medium / High
```

The architecture is designed to preserve relevant colour information while learning spatial and contextual features for ordinal intensity classification.

## 5. Research Methodology

The research methodology consists of the following stages.

**Stage 1 — Dataset Collection**

Collect smartphone photographs of Kesari, Muscat, and Boondhi representing predefined Low, Medium, and High artificial-colour intensity categories.

**Stage 2 — Data Preprocessing**

Inspect image quality, correct image orientation, handle image formats, preserve colour information, examine duplicates, and prepare the dataset for training.

**Stage 3 — Dataset Partitioning**

Create reproducible training, validation, and testing partitions with appropriate controls to minimize sample-level and duplicate-image leakage.

**Stage 4 — Colour-Space Representation**

Generate RGB, HSV, and CIELAB representations from each input image.

**Stage 5 — Adaptive Feature Fusion**

Learn complementary colour-space representations and combine them using sample-dependent gating weights.

**Stage 6 — VMamba Fine-Tuning**

Fine-tune pretrained VMamba-Tiny features using a staged transfer-learning strategy.

**Stage 7 — Ordinal Classification**

Train the CORAL-based prediction head to estimate the ordered artificial-colour intensity categories.

**Stage 8 — Evaluation and Analysis**

Assess prediction performance using classification metrics, ordinal-specific metrics, model comparisons, and explainability methods.

## 6. Comparative Evaluation

The proposed CS-MON architecture is designed to be evaluated against four pretrained deep learning models:

| Model | Role |
|---|---|
| MobileNetV3-Small | Baseline |
| ResNet18 | Baseline |
| ShuffleNetV2 ×1.0 | Baseline |
| MobileNetV2 | Baseline |
| CS-MON (Fine-Tuned VMamba-Tiny) | Proposed model |

All models will be assessed using consistent dataset partitions and evaluation procedures to support fair comparison.

### Evaluation Metrics

The planned evaluation includes:

- Classification Accuracy
- Macro Precision, Recall, and F1-Score
- Ordinal Mean Absolute Error (MAE)
- Quadratic Weighted Kappa (QWK)
- Confusion Matrix
- Per-Class Performance
- Per-Sweet Performance
- Inference Latency and Model Efficiency

Ordinal MAE and QWK are particularly important because the intensity categories have a meaningful order.

## 7. Explainability and Robustness

The research also investigates model interpretability and prediction reliability.

Visual attribution techniques will be used to examine image regions influencing predictions.

Where the available dataset supports it, robustness analysis will investigate variations across sweet categories, illumination conditions, smartphone devices, and image-capture sessions.

These analyses are intended to help identify model limitations and assess its potential for practical preliminary screening.

## 8. Expected Research Contributions

The primary proposed contributions are:

1. **Adaptive Multi-Colour-Space Fusion:** A learnable mechanism combining RGB, HSV, and CIELAB representations.

2. **Fine-Tuned Visual State-Space Learning:** Application of pretrained VMamba-Tiny to colour-sensitive food image analysis.

3. **Monotonic Ordinal Prediction:** Integration of CORAL-based ordinal learning for ordered artificial-colour intensity categories.

4. **Explainable Evaluation:** Investigation of prediction behaviour through attribution, ordinal metrics, and robustness analysis.

The contribution of each component will be examined through comparative experiments and ablation studies.

## 9. Research Scope and Limitations

CS-MON is intended for preliminary image-based estimation of predefined artificial-colour intensity categories.

The system does not directly identify chemical colourants, measure exact dye concentrations, establish toxicity, or certify food safety.

Prediction reliability depends on the quality of the dataset, reference labels, imaging conditions, and the ability of the trained model to generalize to unseen samples.

Laboratory-based analytical methods remain necessary for chemical identification and regulatory verification.

## 10. Expected Outcome

The expected outcome is an evaluated deep learning model capable of estimating Low, Medium, and High artificial-colour intensity levels from smartphone photographs of selected traditional Sri Lankan sweets.

The research will determine whether combining adaptive colour-space fusion, fine-tuned VMamba-Tiny, and ordinal learning offers measurable advantages over established deep learning baselines.

Experimental performance and final conclusions will be reported based on actual validation and testing results.

---

## Research Information

**Research Title:** Explainable Colour-Space VMamba-Ordinal Learning for Artificial Colour Intensity Estimation in Traditional Sweets

**Proposed Model:** CS-MON — Colour-Space Mamba-Ordinal Network

**Research Area:** Computer Vision, Deep Learning, Food Image Analysis, and Ordinal Classification

**Target Foods:** Kesari, Muscat, and Boondhi

**Prediction Categories:** Low, Medium, and High

**Project Type:** Academic Research and Experimental Model Development

---

*This repository branch documents the CS-MON research component, including its proposed architecture, experimental methodology, model training, and evaluation framework.*
