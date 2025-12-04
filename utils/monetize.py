"""
Monetization utility - GitHub Pages ad integration
"""
import urllib.parse

# ======================
# CONFIGURATION
# ======================

# Your GitHub Pages URL (change this!)
GITHUB_PAGE_URL = "https://vignesh42004.github.io/adspage/"

# Enable/Disable monetization (set False to send files directly)
MONETIZATION_ENABLED = True


def create_download_link(
    file_url: str,
    file_name: str,
    file_size: str = "",
    quality: str = "HD"
) -> str:
    """
    Create a monetized download link through GitHub Pages
    
    Args:
        file_url: Direct file URL
        file_name: Name of the file
        file_size: Size of the file (e.g., "1.5 GB")
        quality: Quality of the video (e.g., "720p", "1080p")
    
    Returns:
        Monetized URL string
    """
    encoded_url = urllib.parse.quote(file_url, safe='')
    encoded_name = urllib.parse.quote(file_name, safe='')
    encoded_size = urllib.parse.quote(file_size, safe='')
    encoded_quality = urllib.parse.quote(quality, safe='')
    
    return f"{GITHUB_PAGE_URL}/?url={encoded_url}&name={encoded_name}&size={encoded_size}&quality={encoded_quality}"


def is_monetization_enabled() -> bool:
    """Check if monetization is enabled"""
    return MONETIZATION_ENABLED and GITHUB_PAGE_URL and "YOUR_GITHUB_USERNAME" not in GITHUB_PAGE_URL