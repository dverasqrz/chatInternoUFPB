#!/usr/bin/env python3
"""
Startup script to verify FFmpeg and essential services.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_ffmpeg():
    """Verify FFmpeg is available and working."""
    max_attempts = 5
    delay = 2
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Checking FFmpeg (attempt {attempt + 1}/{max_attempts})...")
            
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info(f"✅ FFmpeg available: {version_line}")
                
                # Test basic functionality
                test_result = subprocess.run(
                    ['ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=1', '-y', '/tmp/test.mp4'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if test_result.returncode == 0:
                    logger.info("✅ FFmpeg functionality test passed")
                    
                    # Clean up test file
                    Path('/tmp/test.mp4').unlink(missing_ok=True)
                    return True
                else:
                    logger.warning(f"FFmpeg functionality test failed: {test_result.stderr}")
            else:
                logger.warning(f"FFmpeg check failed: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg check timed out")
        except Exception as e:
            logger.warning(f"FFmpeg check error: {e}")
        
        if attempt < max_attempts - 1:
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    logger.error("❌ FFmpeg is not available after multiple attempts")
    return False


def check_directories():
    """Ensure required directories exist and are writable."""
    directories = ['/app/uploads', '/app/runtime', '/app/logs']
    
    for directory in directories:
        dir_path = Path(directory)
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = dir_path / '.startup_test'
            test_file.write_text('test')
            test_file.unlink()
            
            logger.info(f"✅ Directory ready: {directory}")
            
        except Exception as e:
            logger.error(f"❌ Directory issue: {directory} - {e}")
            return False
    
    return True


def main():
    """Run startup checks."""
    logger.info("🚀 Starting UFPB Chat System")
    logger.info("=" * 40)
    
    # Check directories
    if not check_directories():
        logger.error("❌ Directory setup failed")
        sys.exit(1)
    
    # Check FFmpeg
    if not check_ffmpeg():
        logger.error("❌ FFmpeg setup failed - video conversion will not work")
        logger.error("Please ensure FFmpeg is properly installed")
        sys.exit(1)
    
    logger.info("✅ All startup checks passed!")
    logger.info("🎬 Video conversion is ready")
    logger.info("🚀 System ready to start")


if __name__ == "__main__":
    main()
