# AI Detection Engine Specification

This document details the visual, acoustic, and sequence correlation algorithms of the **Copyright Center AI Detection Engine**.

---

## 1. Video & Image Hashing (dHash)
Difference Hashing (dHash) evaluates luminance changes between adjacent pixels. It is robust against scaling, aspect ratio changes, and compression artifacts.

### Mathematical Formulation
1.  **Grayscale**: Maps pixel channels using luminance factors:
    $$Y = 0.299R + 0.587G + 0.114B$$
2.  **Downsampling**: Resizes matrix to $9\times8$ (9 columns, 8 rows).
3.  **Horizontal Gradient Checks**: Evaluates if pixel is brighter than its right neighbor:
    $$D(x, y) = P(x, y) > P(x+1, y) \quad \text{for } 0 \le x < 8, \ 0 \le y < 8$$
4.  **Bit Packing**: Concat the 64 bits to form a 16-character hex string.

---

## 2. Acoustic Hashing
Acoustic fingerprinting isolates dominant energy frequencies in the spectrogram to match audio tracks.

### Processing Steps
1.  **Demuxing**: FFmpeg converts the audio track to mono PCM 16-bit 8000Hz WAV format.
2.  **Short-Time Fourier Transform (STFT)**: Analyzes time slices of 1024 samples (128ms intervals).
3.  **Spectral Peak Extraction**: Runs real FFT (`np.fft.rfft`) over each slice, identifying the bin index containing the maximum amplitude.
4.  **Delta Encoding**: Computes relative frequency coordinates differences between adjacent peaks:
    $$\Delta f = f_2 - f_1$$
    This relative spacing remains constant under pitch-shifting distortions.

---

## 3. Sequence Similarity & Alignments
*   **Visual Hashing Matching**: Computes sliding Hamming alignments between the original dHash list $O$ and leak list $L$:
    $$\text{Similarity}_{\text{visual}} = 1.0 - \frac{\text{Hamming}(O, L)}{64}$$
*   **Audio Matching**: Computes the Jaccard index between coordinates set intersections:
    $$\text{Similarity}_{\text{audio}} = \frac{|F_{\text{orig}} \cap F_{\text{leak}}|}{\max(|F_{\text{orig}}|, |F_{\text{leak}}|)}$$
*   **Aggregated Confidence**:
    $$\text{Confidence} = 0.60 \cdot \text{Similarity}_{\text{visual}} + 0.40 \cdot \text{Similarity}_{\text{audio}}$$
*   Verified match triggered if $\text{Confidence} \ge 80\%$.
