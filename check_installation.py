"""
NGO-InvoiceFiler: Installation Check Script
Verifies all components are properly installed and configured.
"""

import sys
import os
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_python_version():
    """Check Python version"""
    print("\n[1/8] Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n[2/8] Checking dependencies...")

    required = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'werkzeug': 'Werkzeug'
    }

    missing = []
    for module, name in required.items():
        try:
            __import__(module)
            print(f"  ✅ {name} installed")
        except ImportError:
            print(f"  ❌ {name} NOT installed")
            missing.append(name.lower())

    if missing:
        print(f"\n  To install missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True

def check_core_files():
    """Check if all core files exist"""
    print("\n[3/8] Checking core files...")

    required_files = [
        'schemas.py',
        'ocr_parser.py',
        'validator.py',
        'filing.py',
        'ledger.py',
        'security.py',
        'main.py',
        'cli.py',
        'test_suite.py',
        'web_app.py'
    ]

    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} NOT FOUND")
            all_exist = False

    return all_exist

def check_web_files():
    """Check if web interface files exist"""
    print("\n[4/8] Checking web interface files...")

    web_files = [
        'web/index.html',
        'web/styles.css',
        'web/app.js'
    ]

    all_exist = True
    for file in web_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} NOT FOUND")
            all_exist = False

    return all_exist

def check_directories():
    """Check if required directories exist"""
    print("\n[5/8] Checking directories...")

    dirs = ['web', 'uploads', 'output']
    for directory in dirs:
        path = Path(directory)
        if path.exists():
            print(f"  ✅ {directory}/ exists")
        else:
            print(f"  ⚠️  {directory}/ not found (will be created at runtime)")

    return True

def check_imports():
    """Check if core modules can be imported"""
    print("\n[6/8] Checking module imports...")

    modules = [
        ('schemas', 'Data schemas'),
        ('ocr_parser', 'OCR parser'),
        ('validator', 'Validator'),
        ('filing', 'Filing system'),
        ('ledger', 'Ledger manager'),
        ('security', 'Security'),
        ('main', 'Main orchestrator')
    ]

    all_ok = True
    for module, name in modules:
        try:
            __import__(module)
            print(f"  ✅ {name} ({module}.py)")
        except Exception as e:
            print(f"  ❌ {name} ({module}.py) - Error: {str(e)[:50]}")
            all_ok = False

    return all_ok

def check_test_suite():
    """Check if test suite can run"""
    print("\n[7/8] Checking test suite...")

    try:
        import test_suite
        print(f"  ✅ Test suite loaded successfully")
        print(f"  ℹ️  Run 'python test_suite.py' to execute all tests")
        return True
    except Exception as e:
        print(f"  ❌ Test suite error: {str(e)[:100]}")
        return False

def check_web_app():
    """Check if web app can be initialized"""
    print("\n[8/8] Checking web application...")

    try:
        from web_app import app
        print(f"  ✅ Flask app initialized successfully")
        print(f"  ℹ️  Run 'python web_app.py' or 'start_server.bat' to start")
        return True
    except Exception as e:
        print(f"  ❌ Web app error: {str(e)[:100]}")
        return False

def main():
    print_header("NGO-InvoiceFiler Installation Check")

    results = []

    # Run all checks
    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Core Files", check_core_files()))
    results.append(("Web Files", check_web_files()))
    results.append(("Directories", check_directories()))
    results.append(("Module Imports", check_imports()))
    results.append(("Test Suite", check_test_suite()))
    results.append(("Web Application", check_web_app()))

    # Summary
    print_header("Installation Check Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")

    print(f"\n  Score: {passed}/{total} checks passed")

    if passed == total:
        print("\n  🎉 All checks passed! Your installation is complete.")
        print("\n  Next steps:")
        print("    1. Run tests:      python test_suite.py")
        print("    2. Start web app:  python web_app.py")
        print("    3. Or use CLI:     python cli.py --help")
        print("\n  📚 Documentation:")
        print("    - QUICKSTART.md  - 5-minute getting started guide")
        print("    - WEB_README.md  - Web application guide")
        print("    - README.md      - Complete documentation")
        print("    - DEMO.md        - Usage examples")
    else:
        print("\n  ⚠️  Some checks failed. Please review errors above.")
        print("\n  Common fixes:")
        print("    - Install dependencies: pip install flask flask-cors werkzeug")
        print("    - Verify all files downloaded correctly")
        print("    - Check Python version >= 3.8")

    print("\n" + "="*60 + "\n")

    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
