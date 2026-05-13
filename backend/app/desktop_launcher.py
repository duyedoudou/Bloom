import os
import socket
import subprocess
import sys
import traceback
import time
import webbrowser
from pathlib import Path

import httpx
import uvicorn


APP_NAME = "Bloom"
PORT_FILE_NAME = "Bloom.port"
LOCK_FILE_NAME = "Bloom.lock"
WINDOWS_MUTEX_NAME = "Local\\BloomLearningAppSingleton"
DEFAULT_PORT = 8765
DEFAULT_ENV = """# LLM API (OpenAI-compatible endpoint)
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# Database
DATABASE_URL={database_url}
"""


def _user_data_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def _ensure_user_env() -> Path:
    configured_path = os.getenv("BLOOM_CONFIG_PATH")
    if configured_path:
        env_path = Path(configured_path)
        data_dir = env_path.parent
    else:
        data_dir = _user_data_dir()
        env_path = data_dir / ".env"

    data_dir.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        database_url = f"sqlite:///{(data_dir / 'bloom.db').as_posix()}"
        env_path.write_text(DEFAULT_ENV.format(database_url=database_url), encoding="utf-8")
    return env_path


def _data_dir_for_env(env_path: Path | None = None) -> Path:
    if env_path:
        return env_path.parent
    return _user_data_dir()


def _log_path(data_dir: Path | None = None) -> Path:
    return _data_dir_for_env(data_dir) / "Bloom.log"


def _write_log(message: str, data_dir: Path | None = None) -> None:
    try:
        path = _log_path(data_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _select_port(data_dir: Path) -> int:
    configured_port = os.getenv("BLOOM_PORT")
    if configured_port:
        return int(configured_port)

    if _is_port_available(DEFAULT_PORT):
        return DEFAULT_PORT

    default_url = f"http://127.0.0.1:{DEFAULT_PORT}"
    if _health_ok(default_url):
        _write_port_file(data_dir, DEFAULT_PORT)
        _open_url(default_url, data_dir)
        os._exit(0)

    return _find_free_port()


def _open_url(url: str, data_dir: Path | None = None) -> bool:
    if os.getenv("BLOOM_NO_BROWSER") == "1":
        _write_log(f"Browser opening skipped for {url}", data_dir)
        return False

    _write_log(f"Opening browser at {url}", data_dir)
    if sys.platform.startswith("win"):
        attempts = [
            ("explorer", lambda: subprocess.Popen(["explorer.exe", url])),
            ("os.startfile", lambda: os.startfile(url)),  # type: ignore[attr-defined]
            ("rundll32", lambda: subprocess.Popen(["rundll32.exe", "url.dll,FileProtocolHandler", url])),
            ("cmd-start", lambda: subprocess.Popen(["cmd.exe", "/c", "start", "", url], shell=False)),
            ("webbrowser", lambda: webbrowser.open(url)),
        ]
    else:
        attempts = [("webbrowser", lambda: webbrowser.open(url))]

    for name, opener in attempts:
        try:
            result = opener()
            if result is False:
                _write_log(f"Browser opener {name} returned false", data_dir)
                continue
            _write_log(f"Browser opener {name} succeeded for {url}", data_dir)
            return True
        except Exception:
            _write_log(f"Browser opener {name} failed:\n{traceback.format_exc()}", data_dir)
    return False


def _health_ok(url: str) -> bool:
    try:
        response = httpx.get(f"{url}/api/health", timeout=0.5, trust_env=False)
        return response.status_code == 200
    except Exception:
        return False


def _open_browser_when_ready(url: str, data_dir: Path | None = None) -> bool:
    health_url = f"{url}/api/health"
    for _ in range(60):
        try:
            response = httpx.get(health_url, timeout=0.5, trust_env=False)
            if response.status_code == 200:
                _open_url(url, data_dir)
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _spawn_browser_opener(url: str, data_dir: Path | None = None) -> None:
    if os.getenv("BLOOM_NO_BROWSER") == "1":
        _write_log(f"External browser opener skipped for {url}", data_dir)
        return

    if not sys.platform.startswith("win"):
        import threading

        opener = threading.Thread(target=_open_browser_when_ready, args=(url, data_dir), daemon=True)
        opener.start()
        return

    import threading

    opener = threading.Thread(target=_open_browser_when_ready, args=(url, data_dir), daemon=True)
    opener.start()

    script = (
        f"$u='{url}';"
        "for($i=0;$i -lt 80;$i++){"
        "try{"
        "$r=Invoke-WebRequest -Uri ($u + '/api/health') -UseBasicParsing -TimeoutSec 1;"
        "if($r.StatusCode -eq 200){Start-Process $u; exit 0}"
        "}catch{};"
        "Start-Sleep -Milliseconds 250"
        "};"
        "Start-Process $u"
    )
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _write_log(f"External browser opener started for {url}", data_dir)
    except Exception:
        _write_log(f"External browser opener failed:\n{traceback.format_exc()}", data_dir)
        _open_browser_when_ready(url, data_dir)


def _port_file(data_dir: Path) -> Path:
    return data_dir / PORT_FILE_NAME


def _read_existing_url(data_dir: Path) -> str | None:
    path = _port_file(data_dir)
    if not path.exists():
        return None
    try:
        port = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None
    return f"http://127.0.0.1:{port}"


def _open_existing_if_ready(data_dir: Path) -> bool:
    url = _read_existing_url(data_dir)
    if not url:
        return False
    for _ in range(40):
        if _health_ok(url):
            _write_log(f"Opening existing Bloom at {url}", data_dir)
            _open_url(url, data_dir)
            return True
        time.sleep(0.25)
    return False


def _acquire_instance_lock(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateMutexW(None, True, WINDOWS_MUTEX_NAME)
        if not handle:
            return None
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            return None
        return handle

    lock_file = (data_dir / LOCK_FILE_NAME).open("a+b")
    try:
        import msvcrt

        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        return lock_file
    except OSError:
        lock_file.close()
        return None


def _write_port_file(data_dir: Path, port: int) -> None:
    _port_file(data_dir).write_text(str(port), encoding="utf-8")


def main() -> None:
    try:
        env_path = _ensure_user_env()
        data_dir = _data_dir_for_env(env_path)

        lock_file = _acquire_instance_lock(data_dir)
        if lock_file is None:
            if _open_existing_if_ready(data_dir):
                os._exit(0)
            _write_log("Another Bloom instance is starting, but it did not become ready.", data_dir)
            os._exit(0)

        port = _select_port(data_dir)
        url = f"http://127.0.0.1:{port}"
        _write_port_file(data_dir, port)

        os.environ["BLOOM_CONFIG_PATH"] = str(env_path)
        os.environ["CORS_ORIGINS"] = url

        from app.main import app

        _write_log(f"Starting Bloom at {url}", data_dir)
        _spawn_browser_opener(url, data_dir)

        uvicorn.run(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
    except Exception:
        _write_log("Startup failed:\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
