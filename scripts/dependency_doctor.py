#!/usr/bin/env python3
"""
MCP Dependency Doctor - Tự động phát hiện và sửa lỗi thiếu dependencies

Script này:
1. Kiểm tra tất cả dependencies có sẵn không
2. Phát hiện tool nào bị lỗi do thiếu deps
3. Đề xuất lệnh cài đặt chính xác
4. Tự động sửa nếu được yêu cầu
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


class DependencyDoctor:
    """Chẩn đoán và điều trị thiếu dependencies."""
    
    # Mapping từ modules đến package names và tools liên quan
    DEPENDENCY_MAP = {
        "faiss": {
            "package": "faiss-cpu",
            "tier": "fast",
            "tools": ["search_codebase"],
            "description": "Vector search engine (FAISS)",
            "critical": True,
        },
        "pycozo": {
            "package": "pycozo[embedded]",
            "tier": "graph-store",
            "tools": ["find_callers", "impact_analysis", "graph_search", "call_chain"],
            "description": "Graph database for dependency analysis",
            "critical": True,
        },
        "sentence_transformers": {
            "package": "sentence-transformers",
            "tier": "all",
            "tools": ["search_codebase"],
            "description": "Local embedding model for semantic search",
            "critical": True,
        },
        "torch": {
            "package": "torch",
            "tier": "all",
            "tools": ["search_codebase"],
            "description": "PyTorch backend for embeddings",
            "critical": False,  # Có fallback
        },
        "tree_sitter": {
            "package": "tree-sitter",
            "tier": "all",
            "tools": ["get_file_context"],
            "description": "AST parsing for accurate code analysis",
            "critical": False,  # Có fallback
        },
        "leann": {
            "package": "leann",
            "tier": "leann",
            "tools": ["search_codebase"],
            "description": "Efficient vector index (97% storage savings)",
            "critical": False,  # FAISS fallback
        },
        "networkx": {
            "package": "networkx",
            "tier": "fast",
            "tools": ["find_callers", "impact_analysis", "graph_search"],
            "description": "Pure Python graph library (fallback)",
            "critical": False,  # igraph preferred
        },
        "igraph": {
            "package": "python-igraph",
            "tier": "all",
            "tools": ["find_callers", "impact_analysis", "graph_search"],
            "description": "Fast graph library with C++ backend",
            "critical": False,  # networkx fallback
        },
        "onnxruntime": {
            "package": "onnxruntime",
            "tier": "all",
            "tools": ["search_codebase"],
            "description": "ONNX acceleration for embeddings (1.4-3x speedup)",
            "critical": False,  # Optimization only
        },
        "rank_bm25": {
            "package": "rank-bm25",
            "tier": "fast",
            "tools": ["search_codebase"],
            "description": "BM25 keyword search for hybrid retrieval",
            "critical": False,  # Vector-only fallback
        },
        "astchunk": {
            "package": "astchunk",
            "tier": "all",
            "tools": ["get_file_context"],
            "description": "AST-aware code chunking (EMNLP 2025)",
            "critical": False,  # Regex fallback
        },
    }
    
    def __init__(self):
        self.missing_deps = []
        self.installed_deps = []
        self.tool_errors = {}
        
    def check_dependency(self, module_name: str) -> bool:
        """Kiểm tra xem module đã được cài chưa."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
    
    def diagnose(self) -> dict:
        """Chẩn đoán toàn bộ dependencies."""
        print("🔍 Đang kiểm tra dependencies...\n")
        
        for module, info in self.DEPENDENCY_MAP.items():
            is_installed = self.check_dependency(module)
            
            if is_installed:
                self.installed_deps.append({
                    "module": module,
                    "package": info["package"],
                    "tier": info["tier"],
                })
                print(f"✅ {info['description']}")
                print(f"   Module: {module} | Package: {info['package']}")
            else:
                self.missing_deps.append({
                    "module": module,
                    "package": info["package"],
                    "tier": info["tier"],
                    "tools": info["tools"],
                    "description": info["description"],
                    "critical": info["critical"],
                })
                print(f"❌ {info['description']}")
                print(f"   Module: {module} | Package: {info['package']} [THIẾU]")
                
                # Mark affected tools
                for tool in info["tools"]:
                    if tool not in self.tool_errors:
                        self.tool_errors[tool] = []
                    self.tool_errors[tool].append(info["package"])
            
            print()
        
        # Summary
        print("="*80)
        print("📊 KẾT QUẢ CHẨN ĐOÁN")
        print("="*80)
        print(f"✅ Đã cài: {len(self.installed_deps)} dependencies")
        print(f"❌ Thiếu: {len(self.missing_deps)} dependencies")
        print(f"⚠️  Tools bị ảnh hưởng: {len(self.tool_errors)} tools")
        
        if self.tool_errors:
            print("\n📋 Tools bị lỗi:")
            for tool, missing in sorted(self.tool_errors.items()):
                print(f"   • {tool}: thiếu {', '.join(missing)}")
        
        return {
            "installed": self.installed_deps,
            "missing": self.missing_deps,
            "affected_tools": self.tool_errors,
        }
    
    def get_install_command(self, tier: str = None, use_uv: bool = True) -> str:
        """Tạo lệnh cài đặt cho tier cụ thể hoặc tất cả."""
        if tier:
            if use_uv:
                return f"uv add ws-ctx-engine[{tier}]"
            else:
                return f"pip install 'ws-ctx-engine[{tier}]'"
        else:
            # Install all missing individually
            if use_uv:
                packages = [dep["package"] for dep in self.missing_deps]
                return "uv add " + " ".join(f'"{pkg}"' for pkg in packages)
            else:
                packages = [dep["package"] for dep in self.missing_deps]
                return "pip install " + " ".join(packages)
    
    def suggest_fix(self) -> str:
        """Đề xuất cách sửa tốt nhất."""
        if not self.missing_deps:
            return "✅ Không cần sửa gì - tất cả dependencies đã được cài!"
        
        # Tính toán tier tối ưu
        missing_tiers = set(dep["tier"] for dep in self.missing_deps)
        critical_missing = [dep for dep in self.missing_deps if dep["critical"]]
        
        suggestions = []
        suggestions.append("\n💡 ĐỀ XUẤT SỬA:")
        suggestions.append("="*80)
        
        if len(missing_tiers) == 1 and list(missing_tiers)[0] == "all":
            # Chỉ cần cài tier "all"
            suggestions.append("\n🎯 Cài đầy đủ (recommended):")
            suggestions.append(f"   {self.get_install_command('all')}")
        elif len(critical_missing) > 2:
            # Nhiều critical dependencies → recommend cài all
            suggestions.append("\n🎯 Cài đầy đủ (recommended - tiết kiệm thời gian):")
            suggestions.append(f"   {self.get_install_command('all')}")
            suggestions.append("\n   Hoặc cài từng cái:")
            for dep in critical_missing:
                suggestions.append(f"   {self.get_install_command(dep['tier'])}")
        else:
            # Ít dependencies → cài riêng lẻ
            suggestions.append("\n🎯 Cài từng dependencies thiếu:")
            for dep in self.missing_deps:
                suggestions.append(f"   # {dep['description']}")
                suggestions.append(f"   {self.get_install_command(dep['tier'])}")
        
        # Quick fix command
        suggestions.append("\n⚡ Quick fix (cài tất cả cùng lúc):")
        suggestions.append(f"   {self.get_install_command()}")
        
        return "\n".join(suggestions)
    
    def auto_fix(self, use_uv: bool = True, dry_run: bool = True) -> bool:
        """Tự động cài đặt thiếu dependencies."""
        if not self.missing_deps:
            print("✅ Không có gì cần cài!")
            return True
        
        print("\n🔧 Bắt đầu tự động cài đặt...\n")
        
        # Ưu tiên critical dependencies trước
        to_install = sorted(
            self.missing_deps,
            key=lambda x: (not x["critical"], x["tier"])
        )
        
        success_count = 0
        failed_packages = []
        
        for dep in to_install:
            package = dep["package"]
            print(f"📦 Đang cài: {package}")
            
            if dry_run:
                print(f"   [DRY RUN] Would install: {package}")
                success_count += 1
            else:
                try:
                    if use_uv:
                        cmd = ["uv", "add", package]
                    else:
                        cmd = [sys.executable, "-m", "pip", "install", package]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        print(f"   ✅ Cài thành công")
                        success_count += 1
                    else:
                        print(f"   ❌ Lỗi: {result.stderr[:200]}")
                        failed_packages.append(package)
                        
                except subprocess.TimeoutExpired:
                    print(f"   ⏱️  Timeout sau 5 phút")
                    failed_packages.append(package)
                except Exception as e:
                    print(f"   ❌ Lỗi: {str(e)}")
                    failed_packages.append(package)
        
        # Summary
        print("\n" + "="*80)
        print("📊 KẾT QUẢ CÀI ĐẶT")
        print("="*80)
        print(f"✅ Thành công: {success_count}/{len(to_install)}")
        
        if failed_packages:
            print(f"❌ Thất bại: {len(failed_packages)}")
            print("\nCác package thất bại:")
            for pkg in failed_packages:
                print(f"   • {pkg}")
            return False
        else:
            print("🎉 Tất cả dependencies đã được cài thành công!")
            print("\n💡 Bây giờ chạy lại lệnh để rebuild index:")
            print("   ws-ctx-engine index . --verbose")
            return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🔍 MCP Dependency Doctor - Chẩn đoán và điều trị thiếu dependencies"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Tự động cài đặt thiếu dependencies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị, không cài thật"
    )
    parser.add_argument(
        "--pip",
        action="store_true",
        help="Dùng pip thay vì uv"
    )
    parser.add_argument(
        "--tier",
        choices=["fast", "all", "graph-store", "leann"],
        help="Cài đặt theo tier cụ thể"
    )
    
    args = parser.parse_args()
    
    # Run diagnosis
    doctor = DependencyDoctor()
    results = doctor.diagnose()
    
    # Show suggestions
    print(doctor.suggest_fix())
    
    # Auto-fix if requested
    if args.fix:
        print("\n" + "="*80)
        confirm = input("🤔 Bạn có muốn tự động cài đặt thiếu dependencies? (y/N): ")
        if confirm.lower() in ['y', 'yes']:
            success = doctor.auto_fix(
                use_uv=not args.pip,
                dry_run=args.dry_run
            )
            sys.exit(0 if success else 1)
        else:
            print("\n💡 Để cài đặt sau, chạy:")
            print(f"   {doctor.get_install_command('all' if len(results['missing']) > 2 else None)}")
    
    # Exit code based on health
    sys.exit(0 if not results["missing"] else 1)


if __name__ == "__main__":
    main()
