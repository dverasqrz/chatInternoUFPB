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
    try:
        logger.info("Checking FFmpeg availability...")
        
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFmpeg available: {version_line}")
            return True
        else:
            logger.warning(f"FFmpeg check failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg check timed out")
        return False
    except Exception as e:
        logger.warning(f"FFmpeg check error: {e}")
        return False


def check_directories():
    """Ensure required directories exist and are writable."""
    directories = ['/opt/projetos/chatZapUFPB/uploads', '/app/runtime', '/app/logs']
    
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
    
    # Check FFmpeg (optional - don't fail if not available)
    if not check_ffmpeg():
        logger.warning("⚠️ FFmpeg not available - video conversion will not work")
        logger.warning("This is OK for basic functionality, but video features will be limited")
    else:
        logger.info("🎬 Video conversion is ready")
    
    logger.info("✅ All startup checks passed!")
    logger.info("🚀 System ready to start")


if __name__ == "__main__":
    main()
