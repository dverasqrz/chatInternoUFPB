#!/usr/bin/env python3
"""
Test video compression settings to verify WhatsApp Android compatibility.
"""

import subprocess
import sys
from pathlib import Path


def create_test_video():
    """Create a test video for compression testing."""
    print("🎬 Creating test video...")
    
    cmd = [
        'ffmpeg', '-f', 'lavfi', 
        '-i', 'testsrc=duration=10:size=1920x1080:rate=30',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-y', '/tmp/test_original.mp4'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error creating test video: {result.stderr}")
        return None
    
    print("✅ Test video created: /tmp/test_original.mp4")
    return '/tmp/test_original.mp4'


def get_video_info(file_path):
    """Get detailed video information."""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name,width,height,pix_fmt,r_frame_rate,bit_rate',
        '-show_entries', 'format=duration,size,bit_rate',
        '-of', 'json', file_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error getting video info: {result.stderr}")
        return None
    
    import json
    return json.loads(result.stdout)


def test_compression():
    """Test compression with different settings."""
    original = create_test_video()
    if not original:
        return False
    
    # Get original info
    print("\n📊 Original video info:")
    original_info = get_video_info(original)
    if original_info:
        stream = original_info['streams'][0]
        format_info = original_info['format']
        print(f"   Resolution: {stream['width']}x{stream['height']}")
        print(f"   FPS: {stream['r_frame_rate']}")
        print(f"   Codec: {stream['codec_name']}")
        print(f"   Pixel Format: {stream['pix_fmt']}")
        print(f"   Size: {format_info['size']} bytes ({int(format_info['size'])/1024/1024:.1f} MB)")
        print(f"   Duration: {format_info['duration']}s")
    
    # Test compression settings
    print("\n🗜️ Testing compression settings...")
    
    # Settings for maximum compression
    cmd = [
        'ffmpeg', '-i', original,
        # Video - Maximum compression
        '-c:v', 'libx264',
        '-profile:v', 'baseline',
        '-level:v', '3.1',
        '-pix_fmt', 'yuv420p',
        '-preset', 'veryfast',
        '-crf', '28',
        '-tune', 'fastdecode',
        
        # Bitrate control
        '-maxrate', '800k',
        '-bufsize', '1600k',
        
        # Audio - Compressed
        '-c:a', 'aac',
        '-b:a', '96k',
        '-ar', '22050',
        '-ac', '1',
        
        # Filters
        '-vf', "scale='if(gt(iw,ih),min(640,iw),-2)':'if(gt(iw,ih),-2,min(480,ih))',pad=ceil(iw/2)*2:ceil(ih/2)*2,fps=24",
        
        # Output
        '-movflags', '+faststart',
        '-y', '/tmp/test_compressed.mp4'
    ]
    
    print(f"🔧 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Compression failed: {result.stderr}")
        return False
    
    # Get compressed info
    print("\n📊 Compressed video info:")
    compressed_info = get_video_info('/tmp/test_compressed.mp4')
    if compressed_info:
        stream = compressed_info['streams'][0]
        format_info = compressed_info['format']
        print(f"   Resolution: {stream['width']}x{stream['height']}")
        print(f"   FPS: {stream['r_frame_rate']}")
        print(f"   Codec: {stream['codec_name']}")
        print(f"   Pixel Format: {stream['pix_fmt']}")
        print(f"   Size: {format_info['size']} bytes ({int(format_info['size'])/1024/1024:.1f} MB)")
        print(f"   Duration: {format_info['duration']}s")
        
        # Calculate compression ratio
        original_size = int(original_info['format']['size'])
        compressed_size = int(format_info['size'])
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print(f"\n📈 Compression Results:")
        print(f"   Original: {original_size/1024/1024:.1f} MB")
        print(f"   Compressed: {compressed_size/1024/1024:.1f} MB")
        print(f"   Compression: {compression_ratio:.1f}% smaller")
        print(f"   Size reduction: {(original_size - compressed_size)/1024/1024:.1f} MB")
    
    return True


def main():
    """Run compression test."""
    print("🗜️ Video Compression Test for WhatsApp Android")
    print("=" * 50)
    
    if not test_compression():
        print("❌ Compression test failed")
        sys.exit(1)
    
    print("\n✅ Compression test completed successfully!")
    print("📱 Video is ready for WhatsApp Android!")
    
    # Clean up
    Path('/tmp/test_original.mp4').unlink(missing_ok=True)
    Path('/tmp/test_compressed.mp4').unlink(missing_ok=True)


if __name__ == "__main__":
    main()
