"""
GUIA: SISTEMA DE ROLES E PERMISSÕES DO AIDO
=============================================

Este guia explica como usar o novo sistema de controle de acesso (RBAC)
no AIDO para gerenciar diferentes níveis de usuários e permissões.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. ROLES DISPONÍVEIS
# ═══════════════════════════════════════════════════════════════════════════════

"""
GUEST (Nível 0)
├─ Acesso mínimo
├─ Pode: visualizar status, chat básico
└─ Ideal para: visitantes, testes

USER (Nível 1) - PADRÃO
├─ Acesso normal
├─ Pode: chat, busca web, ler arquivos, abrir apps, visitar URLs, ler memória
└─ Ideal para: usuários regulares

SUB_ADMIN (Nível 2)
├─ Acesso elevado
├─ Pode: tudo de USER + executar scripts, modificar memória, escrever arquivos, ver logs
└─ Ideal para: moderadores, power users

ADMIN (Nível 3) - MÁXIMO
├─ Acesso completo
├─ Pode: TUDO (incluindo gerenciar usuários, mudar configurações, deletar arquivos)
└─ Ideal para: proprietário do sistema, administradores
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PERMISSÕES DISPONÍVEIS
# ═══════════════════════════════════════════════════════════════════════════════

"""
Permissões por categoria:

LEITURA & VISUALIZAÇÃO:
  • read_memory          - Ler histórico de memória
  • view_status          - Ver status do sistema

AÇÕES BÁSICAS:
  • chat                 - Usar chat com AIDO
  • search_web           - Buscar na web
  • read_files           - Ler arquivos locais

AÇÕES DO PC:
  • open_app             - Abrir aplicações
  • visit_url            - Visitar URLs em browsers
  • execute_script       - Executar scripts Python

MODIFICAÇÕES:
  • write_files          - Escrever/criar arquivos
  • delete_files         - Deletar arquivos
  • modify_memory        - Modificar dados de memória

ADMIN:
  • manage_users         - Criar/editar/deletar usuários
  • change_settings      - Alterar configurações do AIDO
  • view_logs            - Ver logs de auditoria
  • access_system_info   - Acessar informações do sistema
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 3. COMO USAR: SETUP INICIAL
# ═══════════════════════════════════════════════════════════════════════════════

"""
PASSO 1: Criar usuários com roles

```python
import auth
from roles import Role, get_access_control

# Criar um novo usuário
auth.add_user("joao", "senha123")
auth.set_user_role("joao", Role.USER)

# Criar sub-admin
auth.add_user("maria", "senha456")
auth.set_user_role("maria", Role.SUB_ADMIN)

# Criar admin
auth.add_user("pedro", "senha789")
auth.set_user_role("pedro", Role.ADMIN)
```

PASSO 2: Fazer login e obter UserContext

```python
from auth import login_with_role

user_ctx = login_with_role("joao", "senha123")
if user_ctx:
    print(f"Bem-vindo {user_ctx.username}!")
    print(f"Role: {user_ctx.role.name}")
    print(f"Permissões: {user_ctx.get_permissions()}")
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMO USAR: PROTEGER AÇÕES COM DECORADORES
# ═══════════════════════════════════════════════════════════════════════════════

"""
OPÇÃO A: Usar @require_permission (mais granular)

```python
from roles import require_permission, Permission

@require_permission(Permission.SEARCH_WEB)
def search_web(query: str, user_context=None) -> str:
    # Apenas usuários com Permission.SEARCH_WEB podem chamar
    return f"Resultados para: {query}"

# Chamar:
try:
    result = search_web("python", user_context=user_ctx)
except AccessDeniedError:
    print("Você não tem permissão para buscar na web")
```

OPÇÃO B: Usar @require_role (mais simples)

```python
from roles import require_role, Role

@require_role(Role.ADMIN)
def delete_user(username: str, user_context=None) -> bool:
    # Apenas ADMIN (Nível 3+) pode chamar
    return True

# Chamar:
try:
    delete_user("joao", user_context=user_ctx)
except AccessDeniedError:
    print("Apenas ADMIN pode deletar usuários")
```

OPÇÃO C: Usar @admin_only (atalho)

```python
from roles import admin_only

@admin_only
def emergency_shutdown(user_context=None) -> bool:
    # Apenas ADMIN
    return True
```

OPÇÃO D: Controle manual dentro da função

```python
from roles import Permission, AccessDeniedError

def flexible_action(mode: str, user_context=None) -> str:
    if mode == "delete":
        if not user_context.has_permission(Permission.DELETE_FILES):
            raise AccessDeniedError("Cannot delete files")
        # Deletar...
    
    return "Done"
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 5. COMO USAR: GERENCIAR ROLES
# ═══════════════════════════════════════════════════════════════════════════════

"""
PROMOVER usuário:

```python
from auth import set_user_role
from roles import Role

set_user_role("joao", Role.SUB_ADMIN)  # USER -> SUB_ADMIN
```

REBAIXAR usuário:

```python
set_user_role("maria", Role.USER)  # SUB_ADMIN -> USER
```

VER todos os usuários e roles:

```python
from auth import list_all_users

users = list_all_users()
for username, role in users.items():
    print(f"{username}: {role}")
```

VER role específico:

```python
from auth import get_user_role

role = get_user_role("joao")
print(f"Joao é: {role}")
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 6. COMO USAR: VERIFICAR PERMISSÕES NO CÓDIGO
# ═══════════════════════════════════════════════════════════════════════════════

"""
Verificar uma permissão:

```python
if user_ctx.has_permission(Permission.SEARCH_WEB):
    # Fazer algo
```

Verificar ALGUMA de várias permissões:

```python
if user_ctx.has_any_permission(Permission.WRITE_FILES, Permission.DELETE_FILES):
    # Pode modificar arquivos
```

Verificar TODAS as permissões:

```python
if user_ctx.has_all_permissions(Permission.MODIFY_MEMORY, Permission.VIEW_LOGS):
    # Pode fazer ambas as ações
```

Obter todas as permissões:

```python
perms = user_ctx.get_permissions()
for perm in perms:
    print(f"- {perm.value}")
```

Verificar se é admin:

```python
if user_ctx.is_admin():           # SUB_ADMIN ou ADMIN
    # Ação admin-like
    
if user_ctx.is_super_admin():     # Apenas ADMIN
    # Ação super-admin
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 7. INTEGRAÇÃO COM BRAIN.PY E TOOLS.PY
# ═══════════════════════════════════════════════════════════════════════════════

"""
Em brain.py:

```python
from auth import login_with_role
from roles import require_permission, Permission

class AIDOBrain:
    def __init__(self):
        self.user_context = None
    
    def authenticate(self, username: str, password: str):
        self.user_context = login_with_role(username, password)
        if self.user_context:
            print(f"Auth ok: {self.user_context}")
    
    @require_permission(Permission.CHAT)
    def process_message(self, msg: str):
        # Apenas usuários com Permission.CHAT
        return self.process(msg, user_context=self.user_context)
```

Em tools.py:

```python
from roles import require_permission, Permission, AccessDeniedError

@require_permission(Permission.EXECUTE_SCRIPT)
def execute_code(script: str, user_context=None) -> str:
    # Apenas SUB_ADMIN e ADMIN
    exec(script)
    return "Script executado"

@require_permission(Permission.READ_FILES)
def read_local_file(filename: str, user_context=None) -> str:
    # USER e acima
    with open(filename, 'r') as f:
        return f.read()
```
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CENÁRIOS DE USO
# ═══════════════════════════════════════════════════════════════════════════════

"""
CENÁRIO 1: Casa com múltiplos usuários

├─ Duarte (ADMIN)
│  └─ Controla tudo, gerencia outros usuários
│
├─ Filhos (USER)
│  └─ Podem usar chat, buscar web, abrir apps
│  └─ Não podem executar scripts ou deletar arquivos
│
└─ Avó (GUEST)
   └─ Apenas visualiza status e usa chat simples

SETUP:
```python
set_user_role("duarte", Role.ADMIN)
set_user_role("filho1", Role.USER)
set_user_role("avó", Role.GUEST)
```


CENÁRIO 2: Setup corporativo

├─ Admin Geral (ADMIN)
│  └─ Gerencia tudo
│
├─ Admin Departamento (SUB_ADMIN)
│  └─ Gerencia scripts, logs, arquivos
│  └─ Não pode adicionar/remover usuários
│
├─ Funcionários (USER)
│  └─ Usam ferramentas básicas
│  └─ Não podem executar scripts
│
└─ Estagiários (GUEST)
   └─ Visualizam apenas


CENÁRIO 3: Função executiva

├─ CEO (ADMIN)
│  └─ Acesso completo
│
├─ CFO, CTO (SUB_ADMIN)
│  └─ Quase tudo, mas não configuram sistema
│
├─ Diretores (USER)
│  └─ Acesso básico
│  └─ Sem scripts ou deletions
│
└─ Consultores Externos (GUEST)
   └─ Apenas visualizam
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 9. BOAS PRÁTICAS
# ═══════════════════════════════════════════════════════════════════════════════

"""
✓ FAÇA:

1. Sempre passar user_context nas chamadas de função protegidas
   result = search_web("query", user_context=user_ctx)

2. Usar decoradores para proteger funções públicas
   @require_permission(Permission.EXECUTE_SCRIPT)
   def run_script(code):
       pass

3. Usar try/except para pegar AccessDeniedError
   try:
       result = admin_function(user_context=ctx)
   except AccessDeniedError as e:
       log_error(f"Access denied: {e}")

4. Verificar permissões granulares para funcionalidades opcionais
   if user_ctx.has_permission(Permission.DELETE_FILES):
       show_delete_button()

5. Manter roles separados em roles_config.json
   Não hardcodificar roles no código


✗ NÃO FAÇA:

1. Esquecer de passar user_context
   search_web("query")  # ERRADO!

2. Usar apenas Role quando permissões são melhor
   # RUIM:
   @require_role(Role.ADMIN)
   def search_web():  # Por que ADMIN pra buscar web?
   
   # BOM:
   @require_permission(Permission.SEARCH_WEB)
   def search_web():

3. Deixar funções sensíveis desprotegidas
   def delete_all_files():  # ERRADO!
       pass

4. Hardcodificar credenciais ou roles
   if username == "admin" and password == "admin123":  # RUIM!

5. Ignorar AccessDeniedError
   result = admin_function()  # Pode falhar silenciosamente
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 10. TESTES
# ═══════════════════════════════════════════════════════════════════════════════

"""
Para testar o sistema, execute:

```bash
python roles.py                    # Mostra matriz de permissões
python roles_example.py            # Executa exemplos de teste
```

Isso mostrará:
1. Matriz completa de roles x permissões
2. Testes de acesso para cada role (ADMIN, USER, SUB_ADMIN)
3. Sucessos (✓) e bloqueios (✓) esperados
"""

if __name__ == "__main__":
    print(__doc__)
