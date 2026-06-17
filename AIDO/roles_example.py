"""
Exemplo de integração do sistema de roles com as ações do AIDO.
Mostra como usar os decoradores e permissões.
"""

from roles import (
    Permission, Role, UserContext, 
    require_permission, require_role, admin_only,
    AccessDeniedError
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO 1: Proteger ações com PERMISSÕES
# ═══════════════════════════════════════════════════════════════════════════════

@require_permission(Permission.SEARCH_WEB)
def search_web_action(query: str, user_context: UserContext = None) -> str:
    """
    Apenas usuários com permissão SEARCH_WEB podem usar.
    USER e acima têm essa permissão.
    """
    print(f"[{user_context.username}] Searching for: {query}")
    return f"Search results for {query}"


@require_permission(Permission.EXECUTE_SCRIPT)
def execute_script(script_path: str, user_context: UserContext = None) -> bool:
    """
    Apenas SUB_ADMIN e ADMIN podem executar scripts.
    USER não tem essa permissão.
    """
    print(f"[{user_context.username}] Executing: {script_path}")
    return True


@require_permission(Permission.WRITE_FILES, Permission.DELETE_FILES)
def manage_files(action: str, filepath: str, user_context: UserContext = None) -> str:
    """
    Requer WRITE_FILES OU DELETE_FILES.
    Apenas SUB_ADMIN e ADMIN têm essas permissões.
    """
    print(f"[{user_context.username}] {action} on {filepath}")
    return f"File operation completed: {action}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO 2: Proteger ações com ROLES
# ═══════════════════════════════════════════════════════════════════════════════

@require_role(Role.ADMIN)
def manage_users(action: str, target_user: str, user_context: UserContext = None) -> str:
    """
    Apenas ADMIN pode gerenciar usuários.
    """
    print(f"[{user_context.username}] Admin action: {action} on {target_user}")
    return f"User management: {action}"


@require_role(Role.SUB_ADMIN, Role.ADMIN)
def view_audit_logs(user_context: UserContext = None) -> list:
    """
    SUB_ADMIN ou ADMIN podem ver logs.
    USER e GUEST não podem.
    """
    print(f"[{user_context.username}] Viewing audit logs")
    return ["log1", "log2", "log3"]


@admin_only
def change_system_settings(setting: str, value: str, user_context: UserContext = None) -> bool:
    """
    Apenas ADMIN - função especial.
    """
    print(f"[{user_context.username}] Changing {setting} to {value}")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO 3: Controle granular dentro de funções
# ═══════════════════════════════════════════════════════════════════════════════

def complex_action(mode: str, user_context: UserContext = None) -> str:
    """
    Função que tem diferentes comportamentos baseado nas permissões do usuário.
    """
    
    if not user_context:
        raise AccessDeniedError("User context required")
    
    print(f"[{user_context.username}] ({user_context.role.name}) - Action: {mode}")
    
    if mode == "read":
        if user_context.has_permission(Permission.READ_MEMORY):
            return "Memory contents retrieved"
        else:
            raise AccessDeniedError("Cannot read memory")
    
    elif mode == "write":
        if user_context.has_permission(Permission.MODIFY_MEMORY):
            return "Memory updated"
        else:
            raise AccessDeniedError("Cannot modify memory")
    
    elif mode == "delete":
        if user_context.has_permission(Permission.DELETE_FILES):
            return "Files deleted"
        else:
            raise AccessDeniedError("Cannot delete files")
    
    elif mode == "admin_panel":
        if user_context.is_super_admin():
            return "Admin panel opened"
        elif user_context.is_admin():
            return "Limited admin panel opened"
        else:
            raise AccessDeniedError("Admin access required")
    
    return "Action completed"


# ═══════════════════════════════════════════════════════════════════════════════
# EXEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from roles import get_access_control, print_role_permissions
    
    # Mostrar matriz de permissões
    print_role_permissions()
    
    # Setup inicial
    acm = get_access_control()
    acm.set_user_role("duarte", Role.ADMIN)
    acm.set_user_role("joao", Role.USER)
    acm.set_user_role("maria", Role.SUB_ADMIN)
    
    print("\n" + "="*80)
    print("TESTE DE ACESSO - DUARTE (ADMIN)")
    print("="*80)
    
    duarte_ctx = acm.login_user("duarte")
    
    try:
        result = search_web_action("python tutorial", user_context=duarte_ctx)
        print(f"✓ {result}\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    try:
        result = execute_script("script.py", user_context=duarte_ctx)
        print(f"✓ Script executed\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    try:
        result = manage_users("promote", "joao", user_context=duarte_ctx)
        print(f"✓ {result}\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    print("\n" + "="*80)
    print("TESTE DE ACESSO - JOAO (USER)")
    print("="*80)
    
    joao_ctx = acm.login_user("joao")
    
    try:
        result = search_web_action("python tutorial", user_context=joao_ctx)
        print(f"✓ {result}\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    try:
        result = execute_script("script.py", user_context=joao_ctx)
        print(f"✗ Should have failed\n")
    except AccessDeniedError as e:
        print(f"✓ Blocked: {e}\n")
    
    try:
        result = manage_users("promote", "joao", user_context=joao_ctx)
        print(f"✗ Should have failed\n")
    except AccessDeniedError as e:
        print(f"✓ Blocked: {e}\n")
    
    print("\n" + "="*80)
    print("TESTE DE ACESSO - MARIA (SUB_ADMIN)")
    print("="*80)
    
    maria_ctx = acm.login_user("maria")
    
    try:
        result = execute_script("script.py", user_context=maria_ctx)
        print(f"✓ {result}\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    try:
        logs = view_audit_logs(user_context=maria_ctx)
        print(f"✓ Viewed {len(logs)} logs\n")
    except AccessDeniedError as e:
        print(f"✗ Error: {e}\n")
    
    try:
        result = manage_users("promote", "joao", user_context=maria_ctx)
        print(f"✗ Should have failed\n")
    except AccessDeniedError as e:
        print(f"✓ Blocked: {e}\n")
