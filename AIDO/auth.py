"""Authentication system for AIDO — password + face login with RBAC integration."""
import os
import json
import hashlib
import uuid
import platform
import subprocess
from pathlib import Path
from typing import Optional

try:
    from deepface import DeepFace
except Exception:
    DeepFace = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    from roles import Role, UserContext, get_access_control, AccessDeniedError
except ImportError:
    Role = None
    UserContext = None
    AccessDeniedError = Exception


# ── Helpers ───────────────────────────────────────────────────────────────

def get_machine_id():
    """Generate a unique machine ID using Windows hardware UUID."""
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output("wmic csproduct get uuid", shell=True).decode().split("\n")[1].strip()
            return result
    except Exception:
        pass
    return str(uuid.getnode())

def hash_password(password: str, salt: str) -> str:
    """SHA-256 hash with salt."""
    return hashlib.sha256(f"{salt}{password}{salt}".encode()).hexdigest()

def get_auth_path():
    return Path(__file__).parent / "auth.json"

def get_face_path(username: str) -> Path:
    return Path(__file__).parent / f"face_{username.lower()}.jpg"


# ── First-time setup ──────────────────────────────────────────────────────

def setup_first_run():
    """Create auth.json with default admin credentials on first launch."""
    machine_id = get_machine_id()
    salt = hashlib.md5(machine_id.encode()).hexdigest()
    data = {
        "machine_id": machine_id,
        "salt": salt,
        "users": {"duarte": hash_password("admin", salt)},
        "locked": False,
    }
    with open(get_auth_path(), "w") as f:
        json.dump(data, f, indent=2)
    return True


# ── Password auth ─────────────────────────────────────────────────────────

def verify_login(username: str, password: str) -> bool:
    """Check username and password against stored hashes."""
    path = get_auth_path()
    if not path.exists():
        setup_first_run()
    with open(path, "r") as f:
        data = json.load(f)
    salt = data.get("salt", "")
    return data.get("users", {}).get(username.lower()) == hash_password(password, salt)

def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Change password (only works on the original machine)."""
    if not is_home_machine() or not verify_login(username, old_password):
        return False
    path = get_auth_path()
    with open(path, "r") as f:
        data = json.load(f)
    data["users"][username.lower()] = hash_password(new_password, data["salt"])
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return True

def add_user(username: str, password: str) -> bool:
    """Add a new user with default USER role (original machine only)."""
    if not is_home_machine():
        return False
    path = get_auth_path()
    with open(path, "r") as f:
        data = json.load(f)
    if username.lower() in data["users"]:
        return False
    data["users"][username.lower()] = hash_password(password, data["salt"])
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    if Role is not None:
        acm = get_access_control()
        acm.set_user_role(username, Role.USER)
    return True


# ── Face auth ─────────────────────────────────────────────────────────────

def has_face_registered(username: str) -> bool:
    return get_face_path(username).exists()

def register_face(username: str, face_image_path: str) -> bool:
    if not Path(face_image_path).exists():
        return False
    dest = get_face_path(username)
    try:
        Path(face_image_path).replace(dest)
        return True
    except Exception:
        try:
            Path(face_image_path).rename(dest)
            return True
        except Exception:
            return False

def verify_face(username: str, sample_path: str) -> bool:
    """Verify a face image against the registered one using DeepFace."""
    if DeepFace is None:
        return False
    registered = get_face_path(username)
    if not registered.exists() or not Path(sample_path).exists():
        return False
    try:
        result = DeepFace.verify(str(sample_path), str(registered), enforce_detection=False, detector_backend="opencv")
        return bool(result.get("verified", False))
    except Exception:
        return False


# ── Machine binding ───────────────────────────────────────────────────────

def is_home_machine():
    """Check if running on the machine where credentials were created."""
    path = get_auth_path()
    if not path.exists():
        return True
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("machine_id") == get_machine_id()


# ── RBAC integration ──────────────────────────────────────────────────────

def set_user_role(username: str, role: Role) -> bool:
    """Set a user's role."""
    if Role is None:
        return False
    try:
        get_access_control().set_user_role(username, role)
        return True
    except Exception:
        return False

def get_user_role(username: str) -> Optional[str]:
    """Get a user's role name."""
    if Role is None:
        return None
    try:
        role = get_access_control().get_user_role(username)
        return role.name if role else None
    except Exception:
        return None

def login_with_role(username: str, password: str) -> Optional[UserContext]:
    """Authenticate and return a UserContext with permissions."""
    if UserContext is None or not verify_login(username, password):
        return None
    try:
        return get_access_control().login_user(username)
    except Exception:
        return None

def list_all_users() -> dict:
    """List all users and their roles."""
    path = get_auth_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return {u: get_user_role(u) or "USER" for u in data.get("users", {})}
    except Exception:
        return {}


# Bootstrap on import
if not get_auth_path().exists():
    setup_first_run()
