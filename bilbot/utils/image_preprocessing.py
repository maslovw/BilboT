"""
Advanced receipt image pre-processing for OCR using contour detection
and perspective transformation
"""

import logging
import os
from typing import Optional, Tuple, List

import cv2
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
MAX_WIDTH = 1200          # keep original aspect, just cap width
BILATERAL_D = 7           # diameter of pixel neighbourhood
BILATERAL_SIGMA = 30      # controls edge preservation
CLAHE_CLIP = 1.5          # contrast limiting
CLAHE_TILE = 8            # tile size for adaptive histogram equalization
CANNY_LOW = 30            # lower threshold for edge detection
CANNY_HIGH = 100          # upper threshold for edge detection
CONTOUR_APPROX_EPSILON = 0.02  # approximation accuracy as a percentage of perimeter
TRANSFORM_HEIGHT = 900    # target height after perspective transform
MIN_CONTOUR_AREA = 10000  # ignore small contours - increased to filter out noise
DESKEW_MAX_ANGLE = 15     # ignore crazy angles for fallback deskew method

# ---------------------------------------------------------------------------

def preprocess_image(
        image_path: str,
        output_path: Optional[str] = None,
        *,
        allow_rotation: bool = False,
        crop: bool = False,
) -> str:
    """
    One-shot preprocessing routine with advanced contour detection and perspective transformation.
    Simplified implementation based on OpenCV contour detection and perspective transform.
    When ``crop`` is True the receipt is cropped and deskewed using the
    detected contour which helps subsequent OCR steps.
    """
    if output_path is None:
        stem, ext = os.path.splitext(image_path)
        output_path = f"{stem}_preprocessed{ext}"

    # Load the image
    img = cv2.imread(image_path)
    
    # Resize if necessary
    if img.shape[1] > MAX_WIDTH:
        scale = MAX_WIDTH / img.shape[1]
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    
    if crop:
        allow_rotation = True  # cropping implies perspective transform

    # Apply deskew/perspective transform if allowed (also used for cropping)
    if allow_rotation:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply edge detection
        edges = cv2.Canny(blurred, CANNY_LOW, CANNY_HIGH)
        
        # Dilate edges to close gaps
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours in the edge image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter small contours
        contours = [c for c in contours if cv2.contourArea(c) > MIN_CONTOUR_AREA]
        
        if contours:
            # Find the largest contour (assumed to be the document/receipt)
            page = max(contours, key=cv2.contourArea)
            
            # Get the convex hull to simplify the contour
            hull = cv2.convexHull(page)
            
            # Approximate the contour to a polygon
            epsilon = CONTOUR_APPROX_EPSILON * cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, epsilon, True)
            
            # If we have 4 points, apply four-point transform
            if len(approx) == 4:
                quad = approx.reshape(-1, 2)
                img = four_point_warp(img, quad)
            else:
                # Try again with different epsilon values
                epsilon = 0.01 * cv2.arcLength(hull, True)  # Try with smaller epsilon
                approx = cv2.approxPolyDP(hull, epsilon, True)
                
                if len(approx) == 4:
                    quad = approx.reshape(-1, 2)
                    img = four_point_warp(img, quad)
                elif len(approx) > 4:
                    # Get minimum area rectangle as a fallback
                    rect = cv2.minAreaRect(hull)
                    box = cv2.boxPoints(rect)
                    box = box.astype(np.int32)
                    img = four_point_warp(img, box)
                else:
                    logger.warning(f"Expected 4 points but got polygon with {len(approx)} points, falling back to simple deskew")
                    img = _simple_deskew(img)
        else:
            logger.warning("No significant contours found in the image, skipping deskew")
    
    # Apply enhancement
    img = _opencv_enhance(img)
    
    # Save the result
    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info("saved %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _basic_resize(path: str) -> Image.Image:
    """Resize with Pillow – nothing else."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)           # honour device orientation
    if img.width > MAX_WIDTH:
        h = int(img.height * MAX_WIDTH / img.width)
        img = img.resize((MAX_WIDTH, h), Image.LANCZOS)
    return img.convert("RGB")


def _opencv_enhance(img_bgr: np.ndarray) -> np.ndarray:
    """Main pipeline: denoise → contrast → equalize. Keeps grayscale instead of binarizing."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1) gentle denoise that keeps edges soft
    gray = cv2.bilateralFilter(
        gray, BILATERAL_D, BILATERAL_SIGMA, BILATERAL_SIGMA
    )

    # 2) local contrast boost (more gentle)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=(CLAHE_TILE, CLAHE_TILE))
    gray = clahe.apply(gray)

    # Convert back to BGR format for saving, but maintain grayscale appearance
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _simple_deskew(img_bgr: np.ndarray) -> np.ndarray:
    """Simple angle-based deskew when contour method fails."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    coords = np.column_stack(np.where(gray < 255))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle += 90
    if abs(angle) > DESKEW_MAX_ANGLE:
        return img_bgr  # probably a false positive, leave it
    (h, w) = img_bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img_bgr, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def four_point_warp(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Apply a perspective transform to obtain a top-down view of a document.
    
    Args:
        img: Input image (BGR format)
        pts: Four points representing the document corners
    
    Returns:
        Warped image (BGR format)
    """
    # Order points in clockwise order: top-left, top-right, bottom-right, bottom-left
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # Compute the width of the new image
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))
    
    # Compute the height of the new image
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))
    
    # Maintain aspect ratio but set a standard height
    aspect_ratio = max_width / max_height
    max_height = TRANSFORM_HEIGHT
    max_width = int(max_height * aspect_ratio)
    
    # Create destination points for the perspective transform
    dst = np.array([
        [0, 0],                  # top-left
        [max_width - 1, 0],      # top-right
        [max_width - 1, max_height - 1],  # bottom-right
        [0, max_height - 1]      # bottom-left
    ], dtype="float32")
    
    # Calculate the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect.astype("float32"), dst)
    warped = cv2.warpPerspective(img, M, (max_width, max_height))
    
    return warped


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order points in clockwise order: top-left, top-right, bottom-right, bottom-left.
    
    Args:
        pts: Array of four points
        
    Returns:
        Ordered array of points
    """
    # Ensure we have exactly 4 points
    if len(pts) != 4:
        logger.warning(f"Expected 4 points but got {len(pts)}")
        # If we have more than 4, keep the 4 largest points forming the largest quadrilateral
        if len(pts) > 4:
            # Use convex hull to get the outer points
            hull = cv2.convexHull(pts.reshape(-1, 1, 2))
            hull = hull.reshape(-1, 2)
            # Find the 4 points that form the largest quadrilateral
            if len(hull) > 4:
                # Use minimum area rectangle
                rect = cv2.minAreaRect(hull)
                pts = cv2.boxPoints(rect)
            else:
                pts = hull
    
    # Initialize result array
    rect = np.zeros((4, 2), dtype="float32")
    
    # Sum coordinates to find top-left (smallest sum) and bottom-right (largest sum)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right
    
    # Compute the difference between coordinates to find top-right and bottom-left
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    
    return rect
