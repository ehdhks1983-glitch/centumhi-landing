"""폴더를 D드라이브로 옮긴다.

배치 파일(.bat)에 한글을 넣으면 윈도우 cmd가 인코딩을 잘못 읽어 깨지므로,
안내문과 실제 작업은 모두 여기(파이썬)에서 처리한다. .bat은 영문 몇 줄뿐이다.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGET = r"D:\자동화프로그램\순위추적기"
# .venv에는 설치 당시 경로가 박혀 있어 옮기면 깨진다 — 새 위치에서 다시 만든다
SKIP = {".venv", "__pycache__", ".git", ".pytest_cache"}


def _ignore(_dir, names):
    return [n for n in names if n in SKIP or n.endswith(".log")]


def main():
    target = Path(os.environ.get("RANKTRACKER_MOVE_TARGET", DEFAULT_TARGET))
    src = Path(__file__).resolve().parent

    print("=" * 58)
    print(" 순위추적기 — D드라이브로 옮기기")
    print("=" * 58)
    print(f" 지금 위치 : {src}")
    print(f" 옮길 위치 : {target}")
    print()

    if src == target:
        print(" 이미 그 위치에 있습니다. 옮길 필요가 없습니다.")
        return 0

    drive = target.drive or "D:"
    if os.name == "nt" and not Path(drive + "\\").exists():
        print(f" [중단] {drive} 드라이브를 찾을 수 없습니다.")
        print("        외장하드나 USB라면 연결 상태를 확인하세요.")
        return 1

    if (src / "rank_tracker.db").exists():
        print(" * 그동안 쌓인 순위 데이터도 함께 옮겨집니다.")
    else:
        print(" * 아직 순위 데이터가 없습니다. 프로그램 파일만 옮깁니다.")
    print(" * 설치 폴더(.venv)는 옮기면 깨지므로 복사하지 않습니다.")
    print("   새 위치에서 실행.bat 을 누르면 자동으로 다시 만들어집니다.")
    print()

    answer = input(" 진행할까요? (y = 예 / 그 외 = 취소): ").strip().lower()
    if answer not in ("y", "yes", "ㅛ"):
        print(" 취소했습니다.")
        return 0

    print("\n 복사하는 중입니다...")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, target, ignore=_ignore, dirs_exist_ok=True)
    except PermissionError:
        print(" [실패] 쓰기 권한이 없습니다. 다른 폴더를 쓰거나 관리자 권한으로 실행하세요.")
        return 1
    except OSError as e:
        print(f" [실패] 복사 중 오류: {e}")
        print("        남은 저장 공간을 확인하세요.")
        return 1

    if not (target / "main.py").exists():
        print(" [실패] 옮겨진 파일을 확인하지 못했습니다.")
        return 1

    moved_db = (target / "rank_tracker.db").exists()
    print()
    print("=" * 58)
    print(" 완료되었습니다.")
    print("=" * 58)
    print(f" 새 위치 : {target}")
    if moved_db:
        print(" 순위 데이터도 함께 옮겨졌습니다.")
    print()
    print(" 이제 새 폴더의 [실행.bat] 을 눌러 사용하세요.")
    print(" (첫 실행은 설치 때문에 1~2분 걸립니다)")
    print()
    print(" 새 위치에서 정상 동작을 확인한 뒤, 지금 폴더는 직접 지우시면 됩니다.")

    if os.name == "nt":
        try:
            subprocess.run(["explorer", str(target)], check=False)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
