#!/usr/bin/env python3
"""
Deployment Readiness Check Script
Verifies that the application is ready for deployment
"""

import os
import json
from pathlib import Path

def check_backend():
    """Check backend deployment readiness"""
    print("🔍 Checking Backend...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    # Check requirements.txt
    requirements_file = backend_dir / "requirements.txt"
    if requirements_file.exists():
        print("✅ requirements.txt found")
    else:
        print("❌ requirements.txt missing")
    
    # Check Procfile
    procfile = backend_dir / "Procfile"
    if procfile.exists():
        print("✅ Procfile found")
    else:
        print("❌ Procfile missing")
    
    # Check railway.toml
    railway_config = backend_dir / "railway.toml"
    if railway_config.exists():
        print("✅ railway.toml found")
    else:
        print("❌ railway.toml missing")
    
    # Check server.py
    server_file = backend_dir / "server.py"
    if server_file.exists():
        print("✅ server.py found")
    else:
        print("❌ server.py missing")

def check_frontend():
    """Check frontend deployment readiness"""
    print("\n🔍 Checking Frontend...")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    # Check package.json
    package_file = frontend_dir / "package.json"
    if package_file.exists():
        print("✅ package.json found")
        
        # Check build scripts
        with open(package_file) as f:
            package_data = json.load(f)
            scripts = package_data.get("scripts", {})
            if "build" in scripts:
                print("✅ Build script found")
            else:
                print("❌ Build script missing")
    else:
        print("❌ package.json missing")
    
    # Check public/index.html
    index_file = frontend_dir / "public" / "index.html"
    if index_file.exists():
        print("✅ index.html found")
    else:
        print("❌ index.html missing")

def check_environment():
    """Check environment configuration"""
    print("\n🔍 Checking Environment...")
    
    backend_dir = Path(__file__).parent / "backend"
    
    # Check production env template
    prod_env = backend_dir / ".env.production"
    if prod_env.exists():
        print("✅ Production environment template found")
    else:
        print("❌ Production environment template missing")

def check_gitignore():
    """Check .gitignore file"""
    print("\n🔍 Checking Git Configuration...")
    
    gitignore_file = Path(__file__).parent / ".gitignore"
    if gitignore_file.exists():
        print("✅ .gitignore found")
    else:
        print("❌ .gitignore missing")

def main():
    """Run all deployment checks"""
    print("🚀 DEPLOYMENT READINESS CHECK")
    print("=" * 40)
    
    check_backend()
    check_frontend()
    check_environment()
    check_gitignore()
    
    print("\n" + "=" * 40)
    print("✅ Deployment Check Complete!")
    print("\n📋 NEXT STEPS:")
    print("1. Push code to GitHub")
    print("2. Set up MongoDB Atlas")
    print("3. Deploy backend to Railway")
    print("4. Deploy frontend to Vercel")
    print("5. Configure environment variables")

if __name__ == "__main__":
    main()