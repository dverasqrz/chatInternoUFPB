#!/usr/bin/env python3
"""
Verify all system dependencies are properly installed.
"""

import subprocess
import sys
from typing import Dict, List


def run_command(cmd: List[str], timeout: int = 10) -> Dict[str, any]:
    """Run a command and return results."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out',
            'return_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'return_code': -1
        }


def check_ffmpeg():
    """Check FFmpeg installation and codecs."""
    print("🎬 Checking FFmpeg...")
    
    # Check basic installation
    result = run_command(['ffmpeg', '-version'])
    if not result['success']:
        print(f"❌ FFmpeg not installed: {result['stderr']}")
        return False
    
    print("✅ FFmpeg installed")
    
    # Extract version
    first_line = result['stdout'].split('\n')[0]
    print(f"   {first_line}")
    
    # Check codecs
    codecs_result = run_command(['ffmpeg', '-codecs'])
    if codecs_result['success']:
        codecs = codecs_result['stdout']
        
        # Essential codecs for video conversion
        essential_codecs = {
            'libx264': 'H.264 video encoding',
            'libx265': 'H.265/HEVC video encoding',
            'aac': 'AAC audio encoding',
            'mp3': 'MP3 audio encoding',
            'opus': 'Opus audio encoding'
        }
        
        print("   Available codecs:")
        for codec, description in essential_codecs.items():
            if codec in codecs:
                print(f"   ✅ {codec} - {description}")
            else:
                print(f"   ⚠️  {codec} - {description} (not available)")
    
    return True


def check_ffprobe():
    """Check FFprobe installation."""
    print("\n🔍 Checking FFprobe...")
    
    result = run_command(['ffprobe', '-version'])
    if not result['success']:
        print(f"❌ FFprobe not installed: {result['stderr']}")
        return False
    
    print("✅ FFprobe installed")
    first_line = result['stdout'].split('\n')[0]
    print(f"   {first_line}")
    return True


def check_python_packages():
    """Check Python packages."""
    print("\n🐍 Checking Python packages...")
    
    essential_packages = [
        ('fastapi', 'FastAPI web framework'),
        ('sqlalchemy', 'SQLAlchemy ORM'),
        ('psycopg2', 'PostgreSQL adapter'),
        ('passlib', 'Password hashing'),
        ('python_jose', 'JWT handling'),
        ('pydantic', 'Data validation'),
    ]
    
    all_good = True
    for package, description in essential_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package} - {description}")
        except ImportError:
            print(f"   ❌ {package} - {description} (not installed)")
            all_good = False
    
    return all_good


def check_system_resources():
    """Check system resources and permissions."""
    print("\n💻 Checking system resources...")
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage('/')
        free_gb = free // (1024**3)
        
        if free_gb > 1:  # At least 1GB free
            print(f"   ✅ Disk space: {free_gb}GB available")
        else:
            print(f"   ⚠️  Low disk space: {free_gb}GB available")
    except Exception as e:
        print(f"   ❌ Could not check disk space: {e}")
    
    # Check memory
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        for line in meminfo.split('\n'):
            if line.startswith('MemAvailable:'):
                kb = int(line.split()[1])
                mb = kb // 1024
                if mb > 512:  # At least 512MB available
                    print(f"   ✅ Memory: {mb}MB available")
                else:
                    print(f"   ⚠️  Low memory: {mb}MB available")
                break
    except Exception:
        print("   ⚠️  Could not check memory usage")
    
    # Check directory permissions
    from pathlib import Path
    
    directories = ['/app/uploads', '/app/runtime', '/app/logs']
    for directory in directories:
        dir_path = Path(directory)
        if dir_path.exists():
            try:
                test_file = dir_path / '.permission_test'
                test_file.write_text('test')
                test_file.unlink()
                print(f"   ✅ {directory} - writable")
            except Exception as e:
                print(f"   ❌ {directory} - not writable: {e}")
        else:
            print(f"   ⚠️  {directory} - does not exist")


def main():
    """Run all dependency checks."""
    print("🔧 UFPB Chat System - Dependency Verification")
    print("=" * 50)
    
    checks = [
        check_ffmpeg,
        check_ffprobe,
        check_python_packages,
        check_system_resources,
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    
    if all(results):
        print("✅ All dependencies are properly installed!")
        print("🚀 System is ready for video conversion and media processing.")
        return 0
    else:
        print("❌ Some dependencies are missing or misconfigured.")
        print("🔧 Please check the installation and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
