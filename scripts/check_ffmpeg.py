#!/usr/bin/env python3
"""
Script to verify FFmpeg installation and functionality.
"""

import subprocess
import sys
from pathlib import Path


def check_ffmpeg_installation():
    """Check if FFmpeg is properly installed and working."""
    print("🔍 Checking FFmpeg installation...")
    
    try:
        # Check FFmpeg version
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            
            # Extract version info
            first_line = result.stdout.split('\n')[0]
            print(f"   Version: {first_line}")
            
            # Check for essential codecs
            codecs_result = subprocess.run(
                ['ffmpeg', '-codecs'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if codecs_result.returncode == 0:
                # Check for H.264 codec
                if 'libx264' in codecs_result.stdout:
                    print("✅ H.264 codec (libx264) is available")
                else:
                    print("⚠️  H.264 codec (libx264) not found - video conversion may be limited")
                
                # Check for AAC codec
                if 'aac' in codecs_result.stdout:
                    print("✅ AAC codec is available")
                else:
                    print("⚠️  AAC codec not found - audio conversion may be limited")
            
            return True
        else:
            print("❌ FFmpeg installation failed")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg check timed out")
        return False
    except FileNotFoundError:
        print("❌ FFmpeg not found")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def check_ffprobe_installation():
    """Check if FFprobe is properly installed."""
    print("\n🔍 Checking FFprobe installation...")
    
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ FFprobe is installed")
            first_line = result.stdout.split('\n')[0]
            print(f"   Version: {first_line}")
            return True
        else:
            print("❌ FFprobe installation failed")
            return False
            
    except Exception as e:
        print(f"❌ FFprobe check failed: {e}")
        return False


def test_video_conversion():
    """Test basic video conversion functionality."""
    print("\n🧪 Testing video conversion...")
    
    try:
        # Create a simple test video (1 second, black screen)
        test_cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'color=c=black:s=320x240:d=1',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-y', '/tmp/test_video.mp4'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Test video creation successful")
            
            # Verify the created video
            verify_cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,width,height',
                '-of', 'csv=p=0', '/tmp/test_video.mp4'
            ]
            
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
            
            if verify_result.returncode == 0:
                print(f"✅ Video verification successful: {verify_result.stdout.strip()}")
                return True
            else:
                print("❌ Video verification failed")
                return False
        else:
            print("❌ Test video creation failed")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Video conversion test failed: {e}")
        return False


def check_file_permissions():
    """Check if the application can write to necessary directories."""
    print("\n📁 Checking file permissions...")
    
    directories = ['/app/uploads', '/app/runtime', '/app/logs']
    
    for directory in directories:
        dir_path = Path(directory)
        
        if dir_path.exists():
            if dir_path.is_dir():
                # Test write permission
                test_file = dir_path / 'test_write.tmp'
                try:
                    test_file.write_text('test')
                    test_file.unlink()
                    print(f"✅ {directory} - writable")
                except Exception as e:
                    print(f"❌ {directory} - not writable: {e}")
            else:
                print(f"❌ {directory} - not a directory")
        else:
            print(f"⚠️  {directory} - does not exist")


def main():
    """Run all checks."""
    print("🎬 FFmpeg Installation Check for UFPB Chat System")
    print("=" * 50)
    
    ffmpeg_ok = check_ffmpeg_installation()
    ffprobe_ok = check_ffprobe_installation()
    
    if ffmpeg_ok and ffprobe_ok:
        conversion_ok = test_video_conversion()
    else:
        conversion_ok = False
    
    check_file_permissions()
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    
    if ffmpeg_ok and ffprobe_ok and conversion_ok:
        print("✅ All checks passed! Video conversion is ready.")
        return 0
    else:
        print("❌ Some checks failed. Video conversion may not work properly.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
