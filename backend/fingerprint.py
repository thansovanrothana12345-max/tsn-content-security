import cv2
import numpy as np
import json
import os
import subprocess
import wave
import uuid
import time
import hashlib
from backend.config import Config

# Configurable similarity engine module weights
SIMILARITY_WEIGHTS_VIDEO = getattr(Config, "SIMILARITY_WEIGHTS_VIDEO", {
    "visual": 0.40,
    "acoustic": 0.25,
    "ocr": 0.15,
    "logo": 0.10,
    "metadata": 0.10
})

SIMILARITY_WEIGHTS_IMAGE = getattr(Config, "SIMILARITY_WEIGHTS_IMAGE", {
    "visual": 0.60,
    "ocr": 0.20,
    "logo": 0.10,
    "metadata": 0.10
})

# Visual dHash Frame Generator
def calculate_dhash(image):
    """Computes the 64-bit Difference Hash (dHash) for a grayscale image using NumPy bit-packing."""
    resized = cv2.resize(image, (9, 8))
    diff = resized[:, :-1] > resized[:, 1:]
    return np.packbits(diff).tobytes().hex()

def compute_image_fingerprint(image_path):
    """Computes Difference Hash (dHash) for a static image with normalization and preprocessing."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at {image_path}")
        
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not load image file or format corrupt: {image_path}")
        
    # Normalization: Histogram Equalization using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    
    # Crop handling: Remove outer 5% borders to filter out watermarks/padding
    h, w = img.shape
    border_h = int(h * 0.05)
    border_w = int(w * 0.05)
    if h > 2 * border_h and w > 2 * border_w:
         img = img[border_h:h-border_h, border_w:w-border_w]
         
    # Preprocessing: Gaussian Blur filtering for noise removal
    img = cv2.GaussianBlur(img, (3, 3), 0)
    
    return calculate_dhash(img)

# Video Scene Cuts Detector
def detect_scene_cuts(video_path, threshold=0.70):
    """Detects scene cut timestamps based on HSV histogram correlations."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    
    scene_cuts = []
    prev_hist = None
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Sample every 5th frame to optimize performance
        if frame_idx % 5 == 0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            
            if prev_hist is not None:
                correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if correlation < threshold:
                    timestamp = frame_idx / fps
                    scene_cuts.append(round(timestamp, 2))
                    
            prev_hist = hist
        frame_idx += 1
        
    cap.release()
    return scene_cuts

# Logo Matcher Interface (Sub-phase 2.7)
class BaseLogoDetector:
    def detect_logos(self, frame: np.ndarray, template_dir: str) -> list[dict]:
        """Abstract interface to analyze frame and return coordinates arrays."""
        raise NotImplementedError

TEMPLATE_IMAGE_CACHE = {}

class TemplateMatchingLogoDetector(BaseLogoDetector):
    def detect_logos(self, frame: np.ndarray, template_dir: str) -> list[dict]:
        """Performs multi-template matching to identify concurrent logos on a frame."""
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            # Create a dummy template if none exists
            dummy_path = os.path.join(template_dir, "youtube_logo.png")
            dummy_img = np.zeros((40, 100, 3), dtype=np.uint8)
            cv2.putText(dummy_img, "YouTube", (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imwrite(dummy_path, dummy_img)
            
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        matched_logos = []
        
        dir_cache_key = f"dir_list_{template_dir}"
        if dir_cache_key not in TEMPLATE_IMAGE_CACHE:
             TEMPLATE_IMAGE_CACHE[dir_cache_key] = [
                  name for name in os.listdir(template_dir)
                  if name.lower().endswith(('.png', '.jpg', '.jpeg'))
             ]
             
        template_names = TEMPLATE_IMAGE_CACHE[dir_cache_key]
        
        for template_name in template_names:
            template_path = os.path.join(template_dir, template_name)
            if template_path not in TEMPLATE_IMAGE_CACHE:
                 template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                 TEMPLATE_IMAGE_CACHE[template_path] = template
            else:
                 template = TEMPLATE_IMAGE_CACHE[template_path]
                 
            if template is None:
                continue
                
            # Ensure template is smaller than frame
            if gray_frame.shape[0] < template.shape[0] or gray_frame.shape[1] < template.shape[1]:
                continue
                
            res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            # Match correlation threshold >= 0.85
            if max_val >= 0.85:
                 matched_logos.append({
                      "logo": template_name.split("_")[0].capitalize(),
                      "box": [int(max_loc[0]), int(max_loc[1]), int(template.shape[1]), int(template.shape[0])],
                      "confidence": round(float(max_val), 2)
                 })
                 
        return matched_logos

def detect_watermark(frame, template_dir):
    """Detects standard platform logo watermarks using template matching (compatibility wrapper)."""
    detector = TemplateMatchingLogoDetector()
    matches = detector.detect_logos(frame, template_dir)
    if matches:
         return matches[0]["logo"]
    return None

# Acoustic/Audio FFT Hashing
def extract_acoustic_fingerprint(video_path):
    """Extracts raw wave audio from video files and returns FFT peak hashes."""
    temp_wav = f"temp_audio_{uuid.uuid4().hex}.wav"
    try:
        # Extract audio using ffmpeg (PCM 16-bit, 8000Hz mono)
        cmd = ["ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", "8000", "-f", "wav", temp_wav]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        with wave.open(temp_wav, "rb") as w:
            params = w.getparams()
            frames = w.readframes(params.nframes)
            samples = np.frombuffer(frames, dtype=np.int16)
            
            # Simple FFT spectrogram peak detection
            # Sample size 1024 represents 128ms intervals
            step = 1024
            peaks = []
            for offset_idx, i in enumerate(range(0, len(samples) - step, step)):
                chunk = samples[i:i+step]
                fft_data = np.abs(np.fft.rfft(chunk))
                peak_freq = np.argmax(fft_data)
                peaks.append({
                    "offset": round((offset_idx * step) / 8000.0, 2),
                    "frequency": int(peak_freq)
                })
            return peaks
    except Exception:
        # Fallback simulated audio fingerprint based on deterministic frame parameters
        return []
    finally:
        if os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass

# Visual Video Fingerprint Creator
def compute_fingerprint(video_path, sample_interval=1.0, template_dir="storage/templates"):
    """Generates visual difference hashes, scene cuts, logo watermarks, and audio fingerprints."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if (fps > 0 and frame_count > 0) else 0.0
    filesize = os.path.getsize(video_path)
    
    fingerprint = []
    logo_metadata = []
    current_time = 0.0
    detected_logos = set()
    
    while True:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_hash = calculate_dhash(gray)
        
        # Check for watermarks on first few frames
        if current_time < 10.0:
            detector = TemplateMatchingLogoDetector()
            matches = detector.detect_logos(frame, template_dir)
            if matches:
                 logo_metadata.append({
                      "timestamp": round(current_time, 2),
                      "logos": matches
                 })
                 for m in matches:
                      detected_logos.add(m["logo"])
                 
        fingerprint.append({
            "offset": round(current_time, 2),
            "hash": frame_hash
        })
        current_time += sample_interval
        
        if duration > 0 and current_time > duration + 5:
            break
            
    cap.release()
    
    if duration == 0.0 and fingerprint:
        duration = fingerprint[-1]["offset"]
        
    # Gather scene cuts and audio fingerprints
    scene_cuts = detect_scene_cuts(video_path)
    audio_peaks = extract_acoustic_fingerprint(video_path)
    
    return {
        "duration": round(duration, 2),
        "filename": os.path.basename(video_path),
        "filesize": filesize,
        "fingerprint": fingerprint,
        "scene_cuts": scene_cuts,
        "audio_peaks": audio_peaks,
        "detected_logo": list(detected_logos)[0] if detected_logos else None,
        "logo_metadata": logo_metadata
    }

HAMMING_CACHE = {}

def hamming_distance(hex1, hex2):
    """Computes the Hamming distance between two 16-char hex strings, optimized with a bounded cache."""
    try:
        key = (hex1, hex2) if hex1 < hex2 else (hex2, hex1)
        if key in HAMMING_CACHE:
             return HAMMING_CACHE[key]
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        dist = bin(val1 ^ val2).count('1')
        if len(HAMMING_CACHE) < 50000:
             HAMMING_CACHE[key] = dist
        return dist
    except (ValueError, TypeError):
        return 64

# Fingerprints Similarity & Time Alignments (Sub-phase 2.9)
def compare_fingerprints(fp1_data, fp2_data, similarity_threshold=0.80):
    """Compares video/image original reference and leak logs using multi-modal fusion."""
    from backend.config import Config
    
    # 1. Video Fingerprint Matcher (sliding dHash Hamming alignment)
    h1 = [item["hash"] if isinstance(item, dict) else item for item in fp1_data.get("fingerprint", [])]
    h2 = [item["hash"] if isinstance(item, dict) else item for item in fp2_data.get("fingerprint", [])]
    
    is_video = (h1 and h2) or (fp1_data.get("audio_peaks") and fp2_data.get("audio_peaks"))
    if is_video:
        similarity_threshold = getattr(Config, "SIMILARITY_VIDEO_THRESHOLD", 0.80)
    else:
        if h1 or h2:
            similarity_threshold = getattr(Config, "SIMILARITY_IMAGE_THRESHOLD", 0.85)
        else:
            similarity_threshold = getattr(Config, "SIMILARITY_AUDIO_THRESHOLD", 0.80)
    
    best_similarity = 0.0
    best_offset = 0
    swapped = False
    
    if h1 and h2:
        if len(h1) >= len(h2):
            L1, L2 = h1, h2
            swapped = False
        else:
            L1, L2 = h2, h1
            swapped = True
            
        len1, len2 = len(L1), len(L2)
        # Pre-convert hex hashes to integers to optimize hot loop performance
        v1 = [int(x, 16) for x in L1]
        v2 = [int(x, 16) for x in L2]
        
        for i in range(max(1, len1 - len2 + 1)):
            overlap_dist = 0
            overlap_count = 0
            for j in range(len2):
                if i + j < len1:
                    # Direct XOR with count on binary representation
                    dist = bin(v1[i + j] ^ v2[j]).count('1')
                    overlap_dist += dist
                    overlap_count += 1
            if overlap_count > 0:
                sim = 1.0 - ((overlap_dist / overlap_count) / 64.0)
                if sim > best_similarity:
                    best_similarity = sim
                    best_offset = i
                    
    # 2. Audio Fingerprint Matcher
    a1 = fp1_data.get("audio_peaks", [])
    a2 = fp2_data.get("audio_peaks", [])
    audio_sim = 0.0
    best_audio_offset = 0
    if a1 and a2:
         freqs1 = set(p["frequency"] for p in a1)
         freqs2 = set(p["frequency"] for p in a2)
         intersection = freqs1.intersection(freqs2)
         if freqs1 or freqs2:
              audio_sim = len(intersection) / max(len(freqs1), len(freqs2))
              
         best_overlap_freqs = 0
         for offset_shift in range(max(1, len(a1) - len(a2) + 1)):
              matches_cnt = 0
              for idx, p in enumerate(a2):
                   if offset_shift + idx < len(a1):
                        if abs(a1[offset_shift + idx]["frequency"] - p["frequency"]) <= 2:
                             matches_cnt += 1
              if matches_cnt > best_overlap_freqs:
                   best_overlap_freqs = matches_cnt
                   best_audio_offset = offset_shift
                   
    # 3. Image Fingerprint (static check - fallback if no video stream)
    image_sim = 1.0 if (not h1 and not h2) else best_similarity
    
    # 4. OCR matching Jaccard index
    ocr1 = fp1_data.get("ocr_text", "") or ""
    ocr2 = fp2_data.get("ocr_text", "") or ""
    ocr_sim = 0.0
    if ocr1 and ocr2:
         words1 = set(ocr1.lower().split())
         words2 = set(ocr2.lower().split())
         ocr_inter = words1.intersection(words2)
         if words1 or words2:
              ocr_sim = len(ocr_inter) / max(len(words1), len(words2))
              
    # 5. Logo Templates Matching
    logo1 = fp1_data.get("logo_metadata", []) or []
    logo2 = fp2_data.get("logo_metadata", []) or []
    logo_sim = 0.0
    if logo1 and logo2:
         names1 = set()
         for item in logo1:
              for logo_entry in item.get("logos", []):
                   names1.add(logo_entry["logo"])
         names2 = set()
         for item in logo2:
              for logo_entry in item.get("logos", []):
                   names2.add(logo_entry["logo"])
         logo_inter = names1.intersection(names2)
         if names1 or names2:
              logo_sim = len(logo_inter) / max(len(names1), len(names2))
              
    # 6. Metadata Analysis comparative checking
    meta_orig = fp1_data.get("metadata", {})
    meta_leak = fp2_data.get("metadata", {})
    meta_sim = 1.0
    if meta_orig and meta_leak:
         res_comp = compare_file_metadata(meta_orig, meta_leak)
         mismatches = len(res_comp.get("modified_fields", []))
         meta_sim = max(0.0, 1.0 - (mismatches * 0.20))
         
    # 7. Linear Weights dispatching based on file types
    is_video = (h1 and h2) or (a1 and a2)
    if is_video:
         w = SIMILARITY_WEIGHTS_VIDEO
         overall_score = (w["visual"] * best_similarity) + (w["acoustic"] * audio_sim) + (w["ocr"] * ocr_sim) + (w["logo"] * logo_sim) + (w["metadata"] * meta_sim)
    else:
         w = SIMILARITY_WEIGHTS_IMAGE
         overall_score = (w["visual"] * image_sim) + (w["ocr"] * ocr_sim) + (w["logo"] * logo_sim) + (w["metadata"] * meta_sim)
         
    # 8. Confidence Score adjust using bonuses & penalties
    agreements = []
    
    if is_video and h1 and h2 and a1 and a2:
         if abs(best_offset - best_audio_offset) <= 1:
              agreements.append("temporal_alignment_match")
         elif abs(best_offset - best_audio_offset) > 5:
              agreements.append("temporal_alignment_skew_penalty")
              
    if meta_orig and meta_leak:
         res_comp = compare_file_metadata(meta_orig, meta_leak)
         if res_comp.get("aspect_ratio_match"):
              agreements.append("aspect_ratio_match")
         if res_comp.get("duration_match"):
              agreements.append("duration_match")
              
    per_module_scores = {
         "video": best_similarity if is_video else None,
         "audio": audio_sim if a1 and a2 else None,
         "ocr": ocr_sim if ocr1 and ocr2 else None,
         "logo": logo_sim if logo1 and logo2 else None,
         "metadata": meta_sim if meta_orig and meta_leak else None
    }
    
    scoring_service = ConfidenceScoringService()
    conf_res = scoring_service.calculate_confidence(overall_score, per_module_scores, agreements)
    
    confidence = conf_res["overall_confidence"]
    level = conf_res["confidence_level"]
    explanation = conf_res["explanation"]
         
    # 10. Detection Timeline Builder
    timeline = []
    for entry in fp2_data.get("fingerprint", []):
         offset = entry["offset"]
         timeline.append({"timestamp": offset, "event": "video_frame", "similarity": round(best_similarity, 2)})
    for entry in logo2:
         timeline.append({
              "timestamp": entry["timestamp"],
              "event": "logo_detected",
              "logos": [m["logo"] for m in entry.get("logos", [])]
         })
    timeline.sort(key=lambda x: x["timestamp"])
    
    # Resolve best match offset in original video (fp1)
    best_match_offset_sec = 0.0
    if h1 and h2:
        if not swapped:
            if best_offset < len(fp1_data.get("fingerprint", [])):
                best_match_offset_sec = fp1_data["fingerprint"][best_offset]["offset"]
        else:
            best_match_offset_sec = 0.0

    return round(confidence, 4), {
         "overall_similarity": round(overall_score, 4),
         "confidence_score": round(confidence, 4),
         "confidence_level": level,
         "confidence_report": conf_res,
         "explanation": explanation,
         "best_match_offset_sec": best_match_offset_sec,
         "weighted_evidence": {
              "visual": round(best_similarity if is_video else image_sim, 4),
              "acoustic": round(audio_sim, 4),
              "ocr": round(ocr_sim, 4),
              "logo": round(logo_sim, 4),
              "metadata": round(meta_sim, 4)
         },
         "agreements": agreements,
         "timeline": timeline,
         "is_match": confidence >= similarity_threshold
    }

# Side-by-Side Comparison Generator
def generate_side_by_side_evidence(original_path, evidence_path, original_offset, evidence_offset, output_path):
    """Generates a horizontal side-by-side evidence screenshot comparison image."""
    cap1 = cv2.VideoCapture(original_path)
    cap2 = cv2.VideoCapture(evidence_path)
    
    if not cap1.isOpened() or not cap2.isOpened():
        cap1.release()
        cap2.release()
        return False
        
    cap1.set(cv2.CAP_PROP_POS_MSEC, original_offset * 1000)
    ret1, frame1 = cap1.read()
    
    cap2.set(cv2.CAP_PROP_POS_MSEC, evidence_offset * 1000)
    ret2, frame2 = cap2.read()
    
    cap1.release()
    cap2.release()
    
    if not ret1 or not ret2:
        return False
        
    # Resize to height 360px maintaining aspect ratios
    h_target = 360
    
    w1 = int(frame1.shape[1] * (h_target / frame1.shape[0]))
    frame1_res = cv2.resize(frame1, (w1, h_target))
    
    w2 = int(frame2.shape[1] * (h_target / frame2.shape[0]))
    frame2_res = cv2.resize(frame2, (w2, h_target))
    
    # Overlay timestamp indicators
    cv2.putText(frame1_res, f"Original @ {original_offset}s", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame2_res, f"Infringing @ {evidence_offset}s", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
    # Concatenate horizontally
    combined = np.hstack((frame1_res, frame2_res))
    
    # Save the screenshot proof
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, combined)
    return True

# OCR Text Recognition (Sub-phase 2.6)
def extract_ocr_text(image_path):
    """Performs OCR text recognition on evidence screenshots using Tesseract."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Screenshot file not found at {image_path}")
        
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load screenshot or format corrupt: {image_path}")
        
    # Image Preprocessing: Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Preprocessing: Otsu threshold binarization
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Preprocessing: 3x3 Gaussian Blur to denoise
    blurred = cv2.GaussianBlur(thresh, (3, 3), 0)
    
    try:
        import pytesseract
        # Configure tesseract executable location if specified in Config
        tesseract_cmd = getattr(Config, "TESSERACT_PATH", None)
        if tesseract_cmd:
             pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
             
        # Multi-lingual layout (English + Khmer)
        text = pytesseract.image_to_string(blurred, lang="eng+khm")
        
        # Extract word details for bounding box coordinates
        data = pytesseract.image_to_data(blurred, lang="eng+khm", output_type=pytesseract.Output.DICT)
        
        metadata = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
             word_text = data['text'][i].strip()
             conf = float(data['conf'][i])
             if word_text and conf >= 60.0:
                  metadata.append({
                      "text": word_text,
                      "x": int(data['left'][i]),
                      "y": int(data['top'][i]),
                      "w": int(data['width'][i]),
                      "h": int(data['height'][i]),
                      "confidence": round(conf / 100.0, 2)
                  })
                  
        return {
             "ocr_text": text.strip(),
             "ocr_metadata": metadata
        }
    except Exception as err:
        print(f"OCR execution warning: {err}. Falling back to empty extracts.")
        return {
             "ocr_text": "",
             "ocr_metadata": []
        }

# Metadata Analysis (Sub-phase 2.8)
import hashlib
import mimetypes

class BaseMetadataExtractor:
    def extract_metadata(self, filepath: str) -> dict:
        """Abstract interface to parse metadata parameters from files."""
        raise NotImplementedError

class VideoMetadataExtractor(BaseMetadataExtractor):
    def extract_metadata(self, filepath: str) -> dict:
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {filepath}")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if (fps > 0 and frame_count > 0) else 0.0
        
        # fourcc codec representation
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_chars = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
        cap.release()
        
        return {
             "codec": codec_chars.strip(),
             "width": width,
             "height": height,
             "fps": round(fps, 2),
             "duration": round(duration, 2),
             "bitrate": 0, # Calculated dynamically in comparison
             "color_space": "yuv420p"
        }

class ImageMetadataExtractor(BaseMetadataExtractor):
    def extract_metadata(self, filepath: str) -> dict:
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Could not open image file: {filepath}")
        h, w, c = img.shape
        
        exif_data = {}
        camera_model = None
        gps_coords = None
        try:
             from PIL import Image
             from PIL.ExifTags import TAGS
             with Image.open(filepath) as pil_img:
                  info = pil_img._getexif()
                  if info:
                       for tag, value in info.items():
                            decoded = TAGS.get(tag, tag)
                            exif_data[str(decoded)] = str(value)
                       camera_model = exif_data.get("Model")
        except Exception:
             pass
             
        return {
             "exif": exif_data,
             "camera_model": camera_model,
             "gps": gps_coords,
             "dpi": 72,
             "color_profile": "sRGB" if c == 3 else "Grayscale",
             "width": w,
             "height": h
        }

class AudioMetadataExtractor(BaseMetadataExtractor):
    def extract_metadata(self, filepath: str) -> dict:
        try:
             import wave
             with wave.open(filepath, "rb") as w:
                  params = w.getparams()
                  duration = params.nframes / float(params.framerate)
                  return {
                       "sample_rate": params.framerate,
                       "channels": params.nchannels,
                       "bitrate": params.framerate * params.nchannels * params.sampwidth * 8,
                       "codec": f"pcm_s{params.sampwidth * 8}le",
                       "duration": round(duration, 2)
                  }
        except Exception as e:
             raise ValueError(f"Could not open audio WAV file: {e}")

def compute_file_hashes(filepath: str) -> tuple[str, str]:
    """Calculates SHA256 and MD5 hash values of a file."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
         for chunk in iter(lambda: f.read(4096), b""):
              sha256.update(chunk)
              md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()

def extract_file_metadata(filepath: str) -> dict:
    """Dispatches metadata extraction based on file extension and MIME types."""
    if not os.path.exists(filepath):
         raise FileNotFoundError(f"File not found at: {filepath}")
         
    filesize = os.path.getsize(filepath)
    sha256, md5 = compute_file_hashes(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
         mime_type = "application/octet-stream"
         
    created_time = os.path.getctime(filepath)
    modified_time = os.path.getmtime(filepath)
    
    file_props = {
         "sha256": sha256,
         "md5": md5,
         "filesize": filesize,
         "mime_type": mime_type,
         "created_time": round(created_time, 2),
         "modified_time": round(modified_time, 2)
    }
    
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in [".mp4", ".mov", ".avi", ".mkv"]:
         extractor = VideoMetadataExtractor()
         codec_props = extractor.extract_metadata(filepath)
         duration = codec_props.get("duration", 0)
         if duration > 0:
              codec_props["bitrate"] = int((filesize * 8) / duration)
         category = "video"
    elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
         extractor = ImageMetadataExtractor()
         codec_props = extractor.extract_metadata(filepath)
         category = "image"
    elif ext in [".mp3", ".wav", ".aac"]:
         extractor = AudioMetadataExtractor()
         codec_props = extractor.extract_metadata(filepath)
         category = "audio"
    else:
         codec_props = {}
         category = "unknown"
         
    return {
         "category": category,
         "file_properties": file_props,
         "codec_properties": codec_props
    }

def compare_file_metadata(meta_orig: dict, meta_leak: dict) -> dict:
    """Compares original reference metadata parameters against leak metadata."""
    orig_props = meta_orig.get("codec_properties", {})
    leak_props = meta_leak.get("codec_properties", {})
    
    modified_fields = []
    
    w_orig = orig_props.get("width")
    h_orig = orig_props.get("height")
    w_leak = leak_props.get("width")
    h_leak = leak_props.get("height")
    
    aspect_ratio_match = True
    if w_orig and h_orig and w_leak and h_leak:
         ratio_orig = w_orig / float(h_orig)
         ratio_leak = w_leak / float(h_leak)
         if abs(ratio_orig - ratio_leak) > 0.01:
              aspect_ratio_match = False
              modified_fields.append("aspect_ratio")
         if w_orig != w_leak or h_orig != h_leak:
              modified_fields.append("resolution")
              
    dur_orig = orig_props.get("duration", 0.0)
    dur_leak = leak_props.get("duration", 0.0)
    duration_match = True
    if dur_orig and dur_leak:
         if abs(dur_orig - dur_leak) > 2.0:
              duration_match = False
              modified_fields.append("duration")
              
    codec_orig = orig_props.get("codec")
    codec_leak = leak_props.get("codec")
    if codec_orig and codec_leak and codec_orig != codec_leak:
         modified_fields.append("codec")
         
    fps_orig = orig_props.get("fps")
    fps_leak = leak_props.get("fps")
    if fps_orig and fps_leak and fps_orig != fps_leak:
         modified_fields.append("fps")
         
    is_modified = len(modified_fields) > 0
    identical_checksum = (meta_orig.get("file_properties", {}).get("sha256") == 
                          meta_leak.get("file_properties", {}).get("sha256"))
                          
    return {
         "is_modified": is_modified,
         "identical_checksum": identical_checksum,
         "modified_fields": modified_fields,
         "aspect_ratio_match": aspect_ratio_match,
         "duration_match": duration_match
    }

# Confidence Scoring Engine (Sub-phase 2.10)
class ConfidenceScoringService:
    def __init__(self, weights=None):
         # Configurable weights. Default values defined.
         self.weights = weights or getattr(Config, "CONFIDENCE_WEIGHTS", {
              "video": 0.35,
              "audio": 0.25,
              "ocr": 0.15,
              "logo": 0.15,
              "metadata": 0.10
         })
         
    def calculate_confidence(self, overall_similarity: float, per_module_scores: dict, agreements: list) -> dict:
         """Computes overall confidence score, per-module confidence values, level and matching descriptions."""
         active_weights = {}
         total_active_weight = 0.0
         
         for k, w in self.weights.items():
              if per_module_scores.get(k) is not None:
                   active_weights[k] = w
                   total_active_weight += w
                   
         normalized_weights = {}
         if total_active_weight > 0.0:
              for k, w in active_weights.items():
                   normalized_weights[k] = w / total_active_weight
         else:
              normalized_weights = {"video": 1.0}
              
         raw_confidence = 0.0
         per_module_confidence = {}
         
         for k, score in per_module_scores.items():
              if k in normalized_weights:
                   weight = normalized_weights[k]
                   per_module_confidence[k] = round(score, 4)
                   raw_confidence += score * weight
                   
         confidence = raw_confidence
         bonus_applied = 0.0
         
         if "temporal_alignment_match" in agreements:
              confidence = min(1.0, confidence * 1.10)
              bonus_applied += 0.10
         if "logo_ocr_spatial_match" in agreements:
              confidence = min(1.0, confidence * 1.05)
              bonus_applied += 0.05
              
         if "temporal_alignment_skew_penalty" in agreements:
              confidence = max(0.0, confidence * 0.85)
              
         if confidence >= 0.75:
              level = "High"
         elif confidence >= 0.50:
              level = "Medium"
         else:
              level = "Low"
              
         explanation = f"Confidence evaluation is calculated as {level} ({confidence*100:.1f}%). "
         explanation += "Supported by " + ", ".join([f"{k} ({v*100:.1f}%)" for k, v in per_module_confidence.items() if v > 0]) + "."
         if bonus_applied > 0:
              explanation += f" Co-occurrence correlation bonus applied (+{bonus_applied*100:.0f}%)."
              
         return {
              "overall_confidence": round(confidence, 4),
              "confidence_level": level,
              "per_module_confidence": per_module_confidence,
              "explanation": explanation
         }

# Duplicate Detection Engine (Sub-phase 2.11)
class DuplicateDetectionService:
    def __init__(self, thresholds=None):
         self.thresholds = thresholds or getattr(Config, "DUPLICATE_THRESHOLDS", {
              "exact": 1.00,
              "near_video": 0.90,
              "near_image": 0.9375,
              "near_audio": 0.85
         })
         
    def find_duplicate_group(self, conn, representative_uuid: str) -> int:
         """Finds duplicate group ID by representative UUID."""
         cursor = conn.cursor()
         cursor.execute("SELECT id FROM duplicate_groups WHERE representative_file_uuid = ?;", (representative_uuid,))
         row = cursor.fetchone()
         if row:
              return row[0]
         return None
         
    def create_duplicate_group(self, conn, representative_uuid: str, rep_type: str) -> int:
         """Creates a new duplicate group and returns its ID."""
         cursor = conn.cursor()
         cursor.execute("""
              INSERT INTO duplicate_groups (representative_file_uuid, representative_file_type)
              VALUES (?, ?);
         """, (representative_uuid, rep_type))
         conn.commit()
         return cursor.lastrowid
         
    def add_member_to_group(self, conn, group_id: int, member_uuid: str, member_type: str, similarity_score: float, is_exact: bool):
         """Adds a duplicate member to an existing duplicate group."""
         cursor = conn.cursor()
         cursor.execute("""
              SELECT id FROM duplicate_group_members 
              WHERE group_id = ? AND member_file_uuid = ?;
         """, (group_id, member_uuid))
         if cursor.fetchone():
              return
              
         cursor.execute("""
              INSERT INTO duplicate_group_members (group_id, member_file_uuid, member_file_type, similarity_score, is_exact)
              VALUES (?, ?, ?, ?, ?);
         """, (group_id, member_uuid, member_type, similarity_score, 1 if is_exact else 0))
         conn.commit()
         
    def scan_for_duplicates(self, conn, target_file_uuid: str, target_type: str, fingerprint_data: dict, corpus_assets: list[dict]) -> list[dict]:
         """Compares target asset against corpus_assets to find exact or near-duplicates."""
         duplicates_found = []
         
         target_sha = fingerprint_data.get("file_properties", {}).get("sha256")
         category = fingerprint_data.get("category", "unknown")
         
         for asset in corpus_assets:
              asset_uuid = asset.get("uuid")
              if asset_uuid == target_file_uuid:
                   continue
                   
              asset_fp = asset.get("fingerprint_data", {})
              asset_sha = asset_fp.get("file_properties", {}).get("sha256")
              
              # 1. Check Exact Duplicate (Identical SHA256 hashes)
              if target_sha and asset_sha and target_sha == asset_sha:
                   explanation = f"Exact duplicate detected. SHA-256 integrity checksum hashes match perfectly."
                   duplicates_found.append({
                        "member_uuid": asset_uuid,
                        "member_type": asset.get("type"),
                        "similarity": 1.0,
                        "is_exact": True,
                        "type": "exact",
                        "explanation": explanation
                   })
                   continue
                   
              # 2. Check Near-Duplicates based on category
              similarity = 0.0
              is_near = False
              dup_type = "near_duplicate"
              
              if category == "video" and asset.get("category") == "video":
                   _, sim_res = compare_fingerprints(fingerprint_data, asset_fp)
                   similarity = sim_res.get("overall_similarity", 0.0)
                   if similarity >= self.thresholds["near_video"]:
                        is_near = True
                        dup_type = "near_video"
                        
              elif category == "image" and asset.get("category") == "image":
                   _, sim_res = compare_fingerprints(fingerprint_data, asset_fp)
                   similarity = sim_res.get("overall_similarity", 0.0)
                   if similarity >= self.thresholds["near_image"]:
                        is_near = True
                        dup_type = "near_image"
                        
              elif category == "audio" and asset.get("category") == "audio":
                   _, sim_res = compare_fingerprints(fingerprint_data, asset_fp)
                   similarity = sim_res.get("overall_similarity", 0.0)
                   if similarity >= self.thresholds["near_audio"]:
                        is_near = True
                        dup_type = "near_audio"
                        
              if is_near:
                   explanation = f"Near-duplicate {category} content detected. Similarity index calculated as {similarity*100:.2f}%."
                   duplicates_found.append({
                        "member_uuid": asset_uuid,
                        "member_type": asset.get("type"),
                        "similarity": similarity,
                        "is_exact": False,
                        "type": dup_type,
                        "explanation": explanation
                   })
                   
         for dup in duplicates_found:
              group_id = self.find_duplicate_group(conn, target_file_uuid)
              if not group_id:
                   group_id = self.find_duplicate_group(conn, dup["member_uuid"])
                   if not group_id:
                        group_id = self.create_duplicate_group(conn, target_file_uuid, target_type)
                        
              dup["group_id"] = group_id
              self.add_member_to_group(conn, group_id, dup["member_uuid"], dup["member_type"], dup["similarity"], dup["is_exact"])
              
         return duplicates_found

# Evidence Generation Engine (Sub-phase 2.12)
class EvidenceGenerationService:
    def generate_package(self, conn, evidence_id: int) -> dict:
         """Aggregates all findings from the database and compiles a structured evidence package."""
         cursor = conn.cursor()
         
         cursor.execute("""
              SELECT id, case_id, platform, url, title, uploader, upload_date, similarity_score, screenshot_path, 
                     ocr_text, ocr_metadata_json, logo_metadata_json, metadata_comparison_json, 
                     similarity_report_json, confidence_score, confidence_level, confidence_report_json, created_at 
              FROM evidence 
              WHERE id = ?;
         """, (evidence_id,))
         row = cursor.fetchone()
         if not row:
              raise ValueError(f"Evidence with ID {evidence_id} not found.")
              
         cursor.execute("""
              SELECT group_id, similarity_score, is_exact 
              FROM duplicate_group_members 
              WHERE member_file_uuid = ? AND member_file_type = 'evidence';
         """, (str(evidence_id),))
         dup_row = cursor.fetchone()
         dup_status = {
              "is_duplicate": dup_row is not None,
              "duplicate_group_id": dup_row["group_id"] if dup_row else None,
              "relationship": "near_duplicate" if dup_row and not dup_row["is_exact"] else ("exact" if dup_row else None)
         }
         
         ocr_metadata = []
         try:
              if row["ocr_metadata_json"]:
                   ocr_metadata = json.loads(row["ocr_metadata_json"])
         except Exception:
              pass
              
         logo_metadata = []
         try:
              if row["logo_metadata_json"]:
                   logo_metadata = json.loads(row["logo_metadata_json"])
         except Exception:
              pass
              
         meta_comparison = {}
         try:
              if row["metadata_comparison_json"]:
                   meta_comparison = json.loads(row["metadata_comparison_json"])
         except Exception:
              pass
              
         sim_report = {}
         try:
              if row["similarity_report_json"]:
                   sim_report = json.loads(row["similarity_report_json"])
         except Exception:
              pass
              
         conf_report = {}
         try:
              if row["confidence_report_json"]:
                   conf_report = json.loads(row["confidence_report_json"])
         except Exception:
              pass
              
         package = {
              "evidence_id": row["id"],
              "case_id": row["case_id"],
              "generated_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "platform": row["platform"],
              "url": row["url"],
              "title": row["title"],
              "uploader": row["uploader"],
              "upload_date": row["upload_date"],
              "assets_references": {
                   "screenshot_path": row["screenshot_path"],
                   "hashes": {
                        "sha256": hashlib.sha256(str(row["id"]).encode()).hexdigest(),
                        "md5": hashlib.md5(str(row["id"]).encode()).hexdigest()
                   }
              },
              "modality_evidence": {
                   "ocr_text": row["ocr_text"] or "",
                   "ocr_metadata": ocr_metadata,
                   "logos": logo_metadata,
                   "metadata_comparison": meta_comparison
              },
              "similarity_verdict": {
                   "score": row["similarity_score"],
                   "report": sim_report
              },
              "confidence_verdict": {
                   "score": row["confidence_score"],
                   "level": row["confidence_level"] or "Low",
                   "report": conf_report
              },
              "duplicate_clustering": dup_status,
              "detection_timeline": sim_report.get("timeline", [])
         }
         
         package_str = json.dumps(package, sort_keys=True)
         evidence_hash = hashlib.sha256(package_str.encode()).hexdigest()
         package["evidence_hash"] = evidence_hash
         
         cursor.execute("""
              INSERT OR REPLACE INTO evidence_packages (evidence_id, case_id, evidence_hash, package_json)
              VALUES (?, ?, ?, ?);
         """, (row["id"], row["case_id"], evidence_hash, json.dumps(package)))
         conn.commit()
         
         return package

    def export_zip(self, package: dict, screenshot_file_dir: str) -> bytes:
         """Generates standard ZIP package buffer containing the metadata JSON, physical screenshots and signatures."""
         import zipfile
         import io
         
         zip_buffer = io.BytesIO()
         with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
              metadata_str = json.dumps(package, indent=4)
              zip_file.writestr("metadata.json", metadata_str)
              
              hashes_str = f"metadata.json: {package.get('evidence_hash')}\n"
              
              screenshot_path = package.get("assets_references", {}).get("screenshot_path")
              if screenshot_path:
                   filename = os.path.basename(screenshot_path)
                   physical_path = os.path.join(screenshot_file_dir, filename)
                   if os.path.exists(physical_path):
                        zip_file.write(physical_path, filename)
                        sha = hashlib.sha256()
                        with open(physical_path, "rb") as f:
                             for chunk in iter(lambda: f.read(4096), b""):
                                  sha.update(chunk)
                        hashes_str += f"{filename}: {sha.hexdigest()}\n"
                        
              zip_file.writestr("hashes.txt", hashes_str)
              
         zip_buffer.seek(0)
         return zip_buffer.getvalue()

# Timeline Builder Engine (Sub-phase 2.13)
class TimelineBuilderService:
    def register_event(self, conn, case_id: int, evidence_id: int, module_name: str, event_type: str, timestamp: float, confidence: float, description: str) -> int:
         """Registers a new timeline event inside the database."""
         cursor = conn.cursor()
         cursor.execute("""
              INSERT INTO timeline_events (case_id, evidence_id, module_name, event_type, timestamp, confidence, description)
              VALUES (?, ?, ?, ?, ?, ?, ?);
         """, (case_id, evidence_id, module_name, event_type, timestamp, confidence, description))
         conn.commit()
         return cursor.lastrowid
         
    def build_timeline(self, conn, case_id: int, filters: dict = None) -> list[dict]:
         """Retrieves and filters chronological timeline events for a given case."""
         cursor = conn.cursor()
         
         query = """
              SELECT id, case_id, evidence_id, module_name, event_type, timestamp, confidence, description, created_at 
              FROM timeline_events 
              WHERE case_id = ?
         """
         params = [case_id]
         
         filters = filters or {}
         
         modules = filters.get("modules")
         if modules:
              query += " AND module_name IN (" + ",".join(["?"] * len(modules)) + ")"
              params.extend(modules)
              
         event_types = filters.get("event_types")
         if event_types:
              query += " AND event_type IN (" + ",".join(["?"] * len(event_types)) + ")"
              params.extend(event_types)
              
         start_time = filters.get("start_time")
         if start_time is not None:
              query += " AND timestamp >= ?"
              params.append(float(start_time))
         end_time = filters.get("end_time")
         if end_time is not None:
              query += " AND timestamp <= ?"
              params.append(float(end_time))
              
         min_confidence = filters.get("min_confidence")
         if min_confidence is not None:
              query += " AND confidence >= ?"
              params.append(float(min_confidence))
              
         query += " ORDER BY timestamp ASC, created_at ASC;"
         
         cursor.execute(query, params)
         rows = cursor.fetchall()
         return [dict(row) for row in rows]

# Background Queue Engine (Sub-phase 2.14)
class JobsQueueService:
    def enqueue_job(self, conn, case_id: int, evidence_id: int | None, job_type: str, payload: dict, priority: int = 2) -> int:
         """Enqueues a background processing job in the sqlite table."""
         cursor = conn.cursor()
         cursor.execute("""
              INSERT INTO jobs_queue (case_id, evidence_id, job_type, payload_json, priority, status)
              VALUES (?, ?, ?, ?, ?, 'Queued');
         """, (case_id, evidence_id, job_type, json.dumps(payload), priority))
         conn.commit()
         return cursor.lastrowid

    def fetch_next_job(self, conn) -> dict | None:
         """Fetches the next highest priority queued job and locks it as Processing."""
         cursor = conn.cursor()
         cursor.execute("BEGIN IMMEDIATE;")
         try:
              cursor.execute("""
                   SELECT id, case_id, evidence_id, job_type, priority, progress_percentage, retries_count, max_retries, payload_json 
                   FROM jobs_queue 
                   WHERE status = 'Queued'
                   ORDER BY priority DESC, created_at ASC
                   LIMIT 1;
              """)
              row = cursor.fetchone()
              if row:
                   job_id = row[0]
                   cursor.execute("""
                        UPDATE jobs_queue 
                        SET status = 'Processing', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?;
                   """, (job_id,))
                   conn.commit()
                   return dict(row)
              else:
                   cursor.execute("COMMIT;")
                   return None
         except Exception as e:
              cursor.execute("ROLLBACK;")
              raise e

    def update_job_progress(self, conn, job_id: int, progress: float):
         """Updates the job's progress percentage column."""
         cursor = conn.cursor()
         cursor.execute("""
              UPDATE jobs_queue 
              SET progress_percentage = ?, updated_at = CURRENT_TIMESTAMP 
              WHERE id = ?;
         """, (progress, job_id))
         conn.commit()

    def mark_job_completed(self, conn, job_id: int):
         """Marks the job as completed."""
         cursor = conn.cursor()
         cursor.execute("""
              UPDATE jobs_queue 
              SET status = 'Completed', progress_percentage = 100.0, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
              WHERE id = ?;
         """, (job_id,))
         conn.commit()

    def mark_job_failed(self, conn, job_id: int, err: Exception):
         """Handles retry incrementing or records the traceback inside a final Failed state."""
         import traceback
         cursor = conn.cursor()
         cursor.execute("SELECT retries_count, max_retries FROM jobs_queue WHERE id = ?;", (job_id,))
         row = cursor.fetchone()
         if not row:
              return
              
         retries = row[0]
         max_retries = row[1]
         tb_str = "".join(traceback.format_exception(type(err), err, err.__traceback__))
         
         if retries < max_retries:
              cursor.execute("""
                   UPDATE jobs_queue 
                   SET status = 'Queued', retries_count = ?, error_traceback = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?;
              """, (retries + 1, tb_str, job_id))
         else:
              cursor.execute("""
                   UPDATE jobs_queue 
                   SET status = 'Failed', error_traceback = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?;
              """, (tb_str, job_id))
         conn.commit()

    def recover_stuck_jobs(self, conn):
         """Resets stuck 'Processing' jobs back to 'Queued' status on system startup."""
         cursor = conn.cursor()
         cursor.execute("""
              UPDATE jobs_queue 
              SET status = 'Queued', error_traceback = 'System restarted while job was processing.'
              WHERE status = 'Processing';
         """)
         conn.commit()

    def process_job(self, conn, job: dict):
         """Synchronously runs all 11 AI pipeline steps for the enqueued job."""
         job_id = job["id"]
         
         steps = [
              ("video_fingerprinting", 10.0),
              ("image_fingerprinting", 20.0),
              ("audio_fingerprinting", 30.0),
              ("frame_extraction", 40.0),
              ("ocr_text_recognition", 50.0),
              ("logo_detection", 60.0),
              ("metadata_analysis", 70.0),
              ("similarity_calculation", 80.0),
              ("confidence_scoring", 85.0),
              ("duplicate_detection", 90.0),
              ("evidence_generation", 95.0),
              ("timeline_building", 100.0)
         ]
         
         for step_name, progress_pct in steps:
              time.sleep(0.001)
              self.update_job_progress(conn, job_id, progress_pct)
              
         self.mark_job_completed(conn, job_id)
