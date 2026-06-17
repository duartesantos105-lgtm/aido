"""
Role-Based Access Control (RBAC) system para AIDO.
Gerencia níveis de acesso, permissões e controle de ações.
"""

from enum import Enum
from functools import wraps
from typing import Set, Dict, List, Callable, Any
import json
from pathlib import Path


class Role(Enum):
    """Níveis de acesso disponíveis."""
    GUEST = 0          # Acesso mínimo (visualização apenas)
    USER = 1           # Acesso normal (ações básicas)
    SUB_ADMIN = 2      # Acesso elevado (gerenciar sub-usuarios)
    ADMIN = 3          # Acesso completo


class Permission(Enum):
    """Permissões granulares."""
    # Leitura & Visualização
    READ_MEMORY = "read_memory"
    VIEW_STATUS = "view_status"
    
    # Ações Básicas
    CHAT = "chat"
    SEARCH_WEB = "search_web"
    READ_FILES = "read_files"
    
    # PC Actions
    OPEN_APP = "open_app"
    VISIT_URL = "visit_url"
    EXECUTE_SCRIPT = "execute_script"
    
    # Modificações
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    MODIFY_MEMORY = "modify_memory"
    
    # Admin
    MANAGE_USERS = "manage_users"
    CHANGE_SETTINGS = "change_settings"
    VIEW_LOGS = "view_logs"
    ACCESS_SYSTEM_INFO = "access_system_info"


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE-PERMISSION MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

# Definir base permissions
_GUEST_PERMS = {
    Permission.VIEW_STATUS,
    Permission.CHAT,
}

_USER_PERMS = {
    *_GUEST_PERMS,
    Permission.READ_MEMORY,
    Permission.SEARCH_WEB,
    Permission.READ_FILES,
    Permission.OPEN_APP,
    Permission.VISIT_URL,
}

_SUB_ADMIN_PERMS = {
    *_USER_PERMS,
    Permission.EXECUTE_SCRIPT,
    Permission.WRITE_FILES,
    Permission.MODIFY_MEMORY,
    Permission.VIEW_LOGS,
}

_ADMIN_PERMS = {
    *_SUB_ADMIN_PERMS,
    Permission.DELETE_FILES,
    Permission.MANAGE_USERS,
    Permission.CHANGE_SETTINGS,
    Permission.ACCESS_SYSTEM_INFO,
}

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: _GUEST_PERMS,
    Role.USER: _USER_PERMS,
    Role.SUB_ADMIN: _SUB_ADMIN_PERMS,
    Role.ADMIN: _ADMIN_PERMS,
}


# ═══════════════════════════════════════════════════════════════════════════════
# USER CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class UserContext:
    """Contexto do usuário autenticado."""
    
    def __init__(self, username: str, role: Role, user_id: str = None):
        self.username = username
        self.role = role
        self.user_id = user_id or username
        self.authenticated = True
        self.created_at = None
        self.last_login = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Verifica se o usuário tem uma permissão específica."""
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def has_any_permission(self, *permissions: Permission) -> bool:
        """Verifica se tem ALGUMA das permissões listadas."""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, *permissions: Permission) -> bool:
        """Verifica se tem TODAS as permissões listadas."""
        return all(self.has_permission(p) for p in permissions)
    
    def get_permissions(self) -> Set[Permission]:
        """Retorna todas as permissões do usuário."""
        return ROLE_PERMISSIONS.get(self.role, set()).copy()
    
    def get_role_level(self) -> int:
        """Retorna o nível numérico do role (para comparações)."""
        return self.role.value
    
    def is_admin(self) -> bool:
        return self.role in (Role.ADMIN, Role.SUB_ADMIN)
    
    def is_super_admin(self) -> bool:
        return self.role == Role.ADMIN
    
    def __repr__(self) -> str:
        return f"<UserContext {self.username} ({self.role.name})>"


# ═══════════════════════════════════════════════════════════════════════════════
# DECORADORES DE PROTEÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

class AccessDeniedError(Exception):
    """Exceção lançada quando acesso é negado."""
    pass


def require_permission(*permissions: Permission):
    """
    Decorador que requer uma ou mais permissões.
    Uso: @require_permission(Permission.CHAT)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Tenta obter user_context dos kwargs
            user_context = kwargs.get('user_context')
            
            if not user_context:
                raise AccessDeniedError("No user context provided")
            
            if not isinstance(user_context, UserContext):
                raise AccessDeniedError("Invalid user context")
            
            # Verifica se tem alguma das permissões
            if not user_context.has_any_permission(*permissions):
                perm_names = ", ".join(p.value for p in permissions)
                raise AccessDeniedError(
                    f"User '{user_context.username}' does not have required "
                    f"permission(s): {perm_names}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: Role):
    """
    Decorador que requer um role específico ou superior.
    Uso: @require_role(Role.ADMIN)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_context = kwargs.get('user_context')
            
            if not user_context or not isinstance(user_context, UserContext):
                raise AccessDeniedError("No user context provided")
            
            # Se a função foi chamada com um usuário admin, qualquer role >= ao requerido passa
            min_level = min(r.value for r in roles)
            if user_context.get_role_level() < min_level:
                role_names = ", ".join(r.name for r in roles)
                raise AccessDeniedError(
                    f"User '{user_context.username}' has insufficient privileges. "
                    f"Required: {role_names}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """Decorador que permite apenas admins."""
    return require_role(Role.ADMIN)(func)


def user_or_above(func: Callable) -> Callable:
    """Decorador que permite USER ou acima."""
    return require_role(Role.USER, Role.SUB_ADMIN, Role.ADMIN)(func)


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class AccessControlManager:
    """Gerenciador central de controle de acesso."""
    
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path(__file__).parent / "roles_config.json"
        self.current_user: UserContext = None
        self.user_roles: Dict[str, Role] = {}
        self.load_config()
    
    def load_config(self):
        """Carrega configuração de roles."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for username, role_name in data.get("users", {}).items():
                        self.user_roles[username.lower()] = Role[role_name]
            except Exception as e:
                print(f"Error loading roles config: {e}")
    
    def save_config(self):
        """Salva configuração de roles."""
        try:
            data = {
                "users": {
                    username: role.name 
                    for username, role in self.user_roles.items()
                }
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving roles config: {e}")
    
    def set_user_role(self, username: str, role: Role):
        """Define o role de um usuário."""
        self.user_roles[username.lower()] = role
        self.save_config()
    
    def get_user_role(self, username: str) -> Role:
        """Obtém o role de um usuário."""
        return self.user_roles.get(username.lower(), Role.USER)
    
    def login_user(self, username: str) -> UserContext:
        """Cria o contexto de um usuário autenticado."""
        role = self.get_user_role(username)
        user_context = UserContext(username, role)
        self.current_user = user_context
        return user_context
    
    def logout_user(self):
        """Faz logout do usuário."""
        self.current_user = None
    
    def check_permission(self, permission: Permission) -> bool:
        """Verifica se o usuário atual tem uma permissão."""
        if not self.current_user:
            return False
        return self.current_user.has_permission(permission)
    
    def get_current_user(self) -> UserContext:
        """Retorna o usuário atual."""
        return self.current_user
    
    def promote_user(self, username: str, new_role: Role):
        """Promove um usuário para um role superior."""
        current_role = self.get_user_role(username)
        if new_role.value > current_role.value:
            self.set_user_role(username, new_role)
            return True
        return False
    
    def demote_user(self, username: str, new_role: Role):
        """Rebaixa um usuário para um role inferior."""
        current_role = self.get_user_role(username)
        if new_role.value < current_role.value:
            self.set_user_role(username, new_role)
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

_access_control_manager: AccessControlManager = None


def get_access_control():
    """Retorna a instância global do AccessControlManager."""
    global _access_control_manager
    if _access_control_manager is None:
        _access_control_manager = AccessControlManager()
    return _access_control_manager


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

def print_role_permissions():
    """Printa uma tabela com roles e permissões."""
    print("\n" + "="*80)
    print("ROLE-BASED ACCESS CONTROL MATRIX")
    print("="*80)
    
    all_permissions = set()
    for perms in ROLE_PERMISSIONS.values():
        all_permissions.update(perms)
    
    permission_names = sorted([p.value for p in all_permissions])
    
    # Cabeçalho
    header = "Permission".ljust(25)
    for role in Role:
        header += role.name.ljust(12)
    print(header)
    print("-"*80)
    
    # Permissões
    for perm_name in permission_names:
        row = perm_name.ljust(25)
        for role in Role:
            perm = Permission(perm_name)
            has_perm = "✓" if perm in ROLE_PERMISSIONS[role] else ""
            row += has_perm.ljust(12)
        print(row)
    
    print("="*80 + "\n")


if __name__ == "__main__":
    print_role_permissions()
    
    # Exemplo de uso
    acm = get_access_control()
    acm.set_user_role("duarte", Role.ADMIN)
    acm.set_user_role("joao", Role.USER)
    acm.set_user_role("maria", Role.SUB_ADMIN)
    
    print("\nUsers and their roles:")
    for username, role in acm.user_roles.items():
        print(f"  {username}: {role.name}")
