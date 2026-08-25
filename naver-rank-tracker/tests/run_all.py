"""검증 스크립트 전체 실행: python tests/run_all.py"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = ["verify_v11.py", "test_web2.py", "test_multichannel.py",
          "test_stage1.py", "test_stage2.py", "test_stage3.py", "test_stage4.py", "test_stage5.py"]

failed = []
for s in SUITES:
    print(f"\n===== {s} =====")
    r = subprocess.run([sys.executable, os.path.join(HERE, s)])
    if r.returncode != 0:
        failed.append(s)

print("\n" + ("전체 통과 ✅" if not failed else f"실패 스위트: {failed} ❌"))
sys.exit(1 if failed else 0)
