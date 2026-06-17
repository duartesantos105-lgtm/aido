"""
TESTE RÁPIDO - Validar o sistema de roles
Execute este script para testar se tudo está funcionando
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("TESTE: Sistema de Roles do AIDO")
print("="*70)

# Teste 1: Importar módulos
print("\n[1/5] Importando módulos...")
try:
    from roles import (
        Role, Permission, UserContext, AccessControlManager,
        require_permission, require_role, AccessDeniedError,
        ROLE_PERMISSIONS
    )
    import auth
    print("✓ Módulos importados com sucesso")
except Exception as e:
    print(f"✗ Erro ao importar: {e}")
    sys.exit(1)

# Teste 2: Criar UserContext
print("\n[2/5] Criando UserContext...")
try:
    user_admin = UserContext("duarte", Role.ADMIN)
    user_normal = UserContext("joao", Role.USER)
    user_guest = UserContext("maria", Role.GUEST)
    print(f"✓ Admin: {user_admin}")
    print(f"✓ User: {user_normal}")
    print(f"✓ Guest: {user_guest}")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# Teste 3: Verificar permissões
print("\n[3/5] Testando permissões...")
try:
    # Admin deve ter tudo
    assert user_admin.has_permission(Permission.MANAGE_USERS)
    assert user_admin.has_permission(Permission.DELETE_FILES)
    print("✓ Admin tem todas as permissões")
    
    # User normal pode buscar web
    assert user_normal.has_permission(Permission.SEARCH_WEB)
    print("✓ User pode buscar web")
    
    # User normal NÃO pode executar scripts
    assert not user_normal.has_permission(Permission.EXECUTE_SCRIPT)
    print("✓ User NÃO pode executar scripts")
    
    # Guest não pode fazer nada
    assert not user_guest.has_permission(Permission.SEARCH_WEB)
    assert not user_guest.has_permission(Permission.EXECUTE_SCRIPT)
    print("✓ Guest tem permissões limitadas")
    
except AssertionError as e:
    print(f"✗ Erro de permissão: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# Teste 4: Testar decoradores
print("\n[4/5] Testando decoradores...")
try:
    @require_permission(Permission.SEARCH_WEB)
    def protected_search(query: str, user_context=None):
        return f"Searching for: {query}"
    
    # Admin deve conseguir
    result = protected_search("python", user_context=user_admin)
    print(f"✓ Admin consegue chamar função protegida")
    
    # User deve conseguir
    result = protected_search("python", user_context=user_normal)
    print(f"✓ User consegue chamar função protegida")
    
    # Guest NÃO deve conseguir
    try:
        result = protected_search("python", user_context=user_guest)
        print(f"✗ Guest conseguiu chamar (deveria ter falhado)")
        sys.exit(1)
    except AccessDeniedError:
        print(f"✓ Guest foi bloqueado (esperado)")
    
except Exception as e:
    print(f"✗ Erro no decorador: {e}")
    sys.exit(1)

# Teste 5: AccessControlManager
print("\n[5/5] Testando AccessControlManager...")
try:
    acm = AccessControlManager()
    
    # Atribuir roles
    acm.set_user_role("alice", Role.SUB_ADMIN)
    acm.set_user_role("bob", Role.USER)
    
    # Verificar
    assert acm.get_user_role("alice") == Role.SUB_ADMIN
    assert acm.get_user_role("bob") == Role.USER
    print("✓ Roles atribuídos corretamente")
    
    # Login
    alice_ctx = acm.login_user("alice")
    assert alice_ctx.role == Role.SUB_ADMIN
    print("✓ Login bem-sucedido")
    
    # Verificar contexto
    assert alice_ctx.has_permission(Permission.EXECUTE_SCRIPT)
    assert not alice_ctx.has_permission(Permission.MANAGE_USERS)
    print("✓ Permissões de SUB_ADMIN corretas")
    
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# Sucesso!
print("\n" + "="*70)
print("✓ TODOS OS TESTES PASSARAM!")
print("="*70)
print("\nO sistema de RBAC está funcionando corretamente.")
print("Próximo passo: integrar com brain.py e tools.py")
print("\nPara mais informações, ver:")
print("  • RBAC_README.md")
print("  • ROLES_GUIDE.md")
print("  • admin_cli.py")
print("="*70)
