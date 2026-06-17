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
    from roles import (
        Role, UserContext, get_access_control, AccessDeniedError
    )
except ImportError:
    # Se roles.py não estiver disponível, criar stubs
    Role = None
    UserContext = None
    AccessDeniedError = Exception

def get_machine_id():
    """Gera um ID único baseado no hardware do PC."""
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output(
                "wmic csproduct get uuid", shell=True
            ).decode().split("\n")[1].strip()
            return result
    except Exception:
        pass
    # Fallback
    return str(uuid.getnode())

def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}{salt}".encode()).hexdigest()

def get_auth_path():
    return Path(__file__).parent / "auth.json"

def get_face_path(username: str) -> Path:
    return Path(__file__).parent / f"face_{username.lower()}.jpg"

def has_face_registered(username: str) -> bool:
    return get_face_path(username).exists()

def is_home_machine():
    """Verifica se estamos no PC original onde as credenciais foram criadas."""
    path = get_auth_path()
    if not path.exists():
        return True  # Primeira vez, é o PC original
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("machine_id") == get_machine_id()

def setup_first_run():
    """Cria as credenciais na primeira execução."""
    machine_id = get_machine_id()
    salt = hashlib.md5(machine_id.encode()).hexdigest()
    
    users = {
        "duarte": hash_password("admin", salt)
    }
    
    data = {
        "machine_id": machine_id,
        "salt": salt,
        "users": users,
        "locked": False
    }
    
    with open(get_auth_path(), "w") as f:
        json.dump(data, f, indent=2)
    
    return True

def verify_login(username: str, password: str) -> bool:
    """Verifica se o username e password estão corretos."""
    path = get_auth_path()
    
    if not path.exists():
        setup_first_run()
    
    with open(path, "r") as f:
        data = json.load(f)
    
    salt = data.get("salt", "")
    users = data.get("users", {})
    hashed = hash_password(password, salt)
    
    return users.get(username.lower()) == hashed

def verify_face(username: str, sample_path: str) -> bool:
    """Verifica se a imagem capturada coincide com a face registada."""
    if DeepFace is None:
        return False
    registered = get_face_path(username)
    if not registered.exists() or not Path(sample_path).exists():
        return False
    try:
        result = DeepFace.verify(
            str(sample_path),
            str(registered),
            enforce_detection=False,
            detector_backend="opencv"
        )
        return bool(result.get("verified", False))
    except Exception:
        return False


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


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Muda a password — só funciona no PC original."""
    if not is_home_machine():
        return False
    
    if not verify_login(username, old_password):
        return False
    
    path = get_auth_path()
    with open(path, "r") as f:
        data = json.load(f)
    
    salt = data["salt"]
    data["users"][username.lower()] = hash_password(new_password, salt)
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
    return True

def add_user(username: str, password: str) -> bool:
    """Adiciona utilizador — só funciona no PC original."""
    if not is_home_machine():
        return False
    
    path = get_auth_path()
    with open(path, "r") as f:
        data = json.load(f)
    
    if username.lower() in data["users"]:
        return False  # Usuário já existe
    
    salt = data["salt"]
    data["users"][username.lower()] = hash_password(password, salt)
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Adicionar ao sistema de roles com Role padrão (USER)
    if Role is not None:
        from roles import get_access_control
        acm = get_access_control()
        acm.set_user_role(username, Role.USER)
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE-BASED ACCESS INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def set_user_role(username: str, role: Role) -> bool:
    """Define o role de um usuário — requer ser admin."""
    if Role is None:
        return False
    
    try:
        from roles import get_access_control
        acm = get_access_control()
        acm.set_user_role(username, role)
        return True
    except Exception:
        return False


def get_user_role(username: str) -> Optional[str]:
    """Obtém o role de um usuário."""
    if Role is None:
        return None
    
    try:
        from roles import get_access_control
        acm = get_access_control()
        role = acm.get_user_role(username)
        return role.name if role else None
    except Exception:
        return None


def login_with_role(username: str, password: str) -> Optional[UserContext]:
    """
    Faz login e retorna UserContext com permissões.
    Retorna None se falhar.
    """
    if UserContext is None:
        return None
    
    # Verificar credenciais
    if not verify_login(username, password):
        return None
    
    try:
        from roles import get_access_control
        acm = get_access_control()
        user_context = acm.login_user(username)
        return user_context
    except Exception:
        return None


def list_all_users() -> dict:
    """Lista todos os usuários e seus roles."""
    path = get_auth_path()
    
    if not path.exists():
        return {}
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
        
        users = {}
        for username in data.get("users", {}).keys():
            role = get_user_role(username)
            users[username] = role or "USER"
        
        return users
    except Exception:
        return {}

# Cria o ficheiro na primeira vez
if not get_auth_path().exists():
    setup_first_run()
