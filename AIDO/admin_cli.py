"""
ADMIN CLI - Interface de linha de comando para gerenciar AIDO
Permite gerenciar usuários, roles e permissões facilmente.
"""

import sys
import getpass
from typing import Optional
import auth
from roles import Role, Permission, get_access_control, print_role_permissions


def print_menu():
    """Menu principal."""
    print("\n" + "="*60)
    print("AIDO - ADMIN CLI v1.0")
    print("="*60)
    print("1. Listar usuários e roles")
    print("2. Criar novo usuário")
    print("3. Deletar usuário")
    print("4. Mudar role de usuário")
    print("5. Ver matriz de permissões")
    print("6. Ver permissões de um usuário")
    print("7. Mudar password")
    print("8. Sair")
    print("="*60)


def list_users():
    """Lista todos os usuários."""
    users = auth.list_all_users()
    
    if not users:
        print("\n✗ Nenhum usuário encontrado.")
        return
    
    print("\n" + "="*60)
    print("USUÁRIOS DO SISTEMA")
    print("="*60)
    print(f"{'Username':<20} {'Role':<15} {'Nível':<10}")
    print("-"*60)
    
    for username, role_name in sorted(users.items()):
        try:
            role = Role[role_name]
            level = role.value
            level_name = ["GUEST", "USER", "SUB_ADMIN", "ADMIN"][level]
            print(f"{username:<20} {role_name:<15} {level_name:<10}")
        except:
            print(f"{username:<20} {role_name:<15} {'?':<10}")
    
    print("="*60)


def create_user():
    """Cria novo usuário."""
    print("\n" + "="*60)
    print("CRIAR NOVO USUÁRIO")
    print("="*60)
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username não pode estar vazio.")
        return
    
    # Verificar se já existe
    users = auth.list_all_users()
    if username.lower() in [u.lower() for u in users.keys()]:
        print(f"✗ Usuário '{username}' já existe.")
        return
    
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirmar password: ")
    
    if password != password_confirm:
        print("✗ Passwords não coincidem.")
        return
    
    if len(password) < 4:
        print("✗ Password muito curta (mínimo 4 caracteres).")
        return
    
    print("\nEscolha o role:")
    print("0. GUEST")
    print("1. USER (padrão)")
    print("2. SUB_ADMIN")
    print("3. ADMIN")
    
    try:
        role_choice = int(input("Role (0-3, padrão 1): ").strip() or "1")
        if role_choice not in range(4):
            print("✗ Role inválido.")
            return
        role = list(Role)[role_choice]
    except:
        print("✗ Input inválido.")
        return
    
    # Criar usuário
    if not auth.add_user(username, password):
        print("✗ Erro ao criar usuário.")
        return
    
    # Atribuir role
    auth.set_user_role(username, role)
    
    print(f"\n✓ Usuário '{username}' criado com sucesso!")
    print(f"  Role: {role.name}")


def delete_user():
    """Deleta um usuário."""
    print("\n" + "="*60)
    print("DELETAR USUÁRIO")
    print("="*60)
    
    username = input("Username para deletar: ").strip()
    if not username:
        print("✗ Username não pode estar vazio.")
        return
    
    users = auth.list_all_users()
    if username.lower() not in [u.lower() for u in users.keys()]:
        print(f"✗ Usuário '{username}' não existe.")
        return
    
    # Confirmação
    confirm = input(f"Tem certeza que quer deletar '{username}'? (sim/não): ")
    if confirm.lower() != "sim":
        print("Operação cancelada.")
        return
    
    # Nota: auth.py não tem função delete_user nativa
    # Precisaria adicionar isso ao auth.py
    print("\n⚠ Função de delete ainda não implementada.")
    print("  Remova manualmente do auth.json se necessário.")


def change_role():
    """Muda o role de um usuário."""
    print("\n" + "="*60)
    print("MUDAR ROLE DE USUÁRIO")
    print("="*60)
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username não pode estar vazio.")
        return
    
    users = auth.list_all_users()
    if username.lower() not in [u.lower() for u in users.keys()]:
        print(f"✗ Usuário '{username}' não existe.")
        return
    
    print("\nEscolha o novo role:")
    print("0. GUEST")
    print("1. USER")
    print("2. SUB_ADMIN")
    print("3. ADMIN")
    
    try:
        role_choice = int(input("Novo role (0-3): ").strip())
        if role_choice not in range(4):
            print("✗ Role inválido.")
            return
        new_role = list(Role)[role_choice]
    except:
        print("✗ Input inválido.")
        return
    
    auth.set_user_role(username, new_role)
    print(f"\n✓ Role de '{username}' mudado para {new_role.name}!")


def view_permissions():
    """Mostra matriz de permissões."""
    print()
    print_role_permissions()


def view_user_permissions():
    """Mostra permissões de um usuário específico."""
    print("\n" + "="*60)
    print("PERMISSÕES DE USUÁRIO")
    print("="*60)
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username não pode estar vazio.")
        return
    
    role_name = auth.get_user_role(username)
    if not role_name:
        print(f"✗ Usuário '{username}' não existe.")
        return
    
    try:
        role = Role[role_name]
    except:
        print(f"✗ Role inválido: {role_name}")
        return
    
    # Obter permissões
    from roles import ROLE_PERMISSIONS
    perms = ROLE_PERMISSIONS.get(role, set())
    
    print(f"\nPermissões de '{username}' ({role.name}):")
    print("-"*60)
    
    if not perms:
        print("Nenhuma permissão")
    else:
        for i, perm in enumerate(sorted(perms, key=lambda p: p.value), 1):
            print(f"{i:2}. {perm.value}")
    
    print("="*60)


def change_password():
    """Muda password de um usuário."""
    print("\n" + "="*60)
    print("MUDAR PASSWORD")
    print("="*60)
    
    username = input("Username: ").strip()
    if not username:
        print("✗ Username não pode estar vazio.")
        return
    
    users = auth.list_all_users()
    if username.lower() not in [u.lower() for u in users.keys()]:
        print(f"✗ Usuário '{username}' não existe.")
        return
    
    # Pedir password atual
    print("\nAutenticação necessária para mudar password:")
    old_password = getpass.getpass("Password atual: ")
    
    if not auth.verify_login(username, old_password):
        print("✗ Password incorreta.")
        return
    
    # Nova password
    new_password = getpass.getpass("Nova password: ")
    new_password_confirm = getpass.getpass("Confirmar nova password: ")
    
    if new_password != new_password_confirm:
        print("✗ Passwords não coincidem.")
        return
    
    if len(new_password) < 4:
        print("✗ Password muito curta (mínimo 4 caracteres).")
        return
    
    if auth.change_password(username, old_password, new_password):
        print(f"\n✓ Password de '{username}' mudada com sucesso!")
    else:
        print("✗ Erro ao mudar password.")


def main():
    """Loop principal."""
    print("\n🔐 Bem-vindo ao AIDO Admin CLI!")
    print("Você precisa de permissões de admin para usar esta ferramenta.")
    
    # Simples: se tem auth.json, permite usar
    # Em produção, você poderia adicionar autenticação aqui
    print("\n⚠ Disclaimer: Esta ferramenta é para administradores.")
    print("  Tenha cuidado ao gerenciar usuários e permissões!\n")
    
    while True:
        print_menu()
        choice = input("Escolha (1-8): ").strip()
        
        if choice == "1":
            list_users()
        elif choice == "2":
            create_user()
        elif choice == "3":
            delete_user()
        elif choice == "4":
            change_role()
        elif choice == "5":
            view_permissions()
        elif choice == "6":
            view_user_permissions()
        elif choice == "7":
            change_password()
        elif choice == "8":
            print("\n✓ Saindo...")
            break
        else:
            print("✗ Opção inválida.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Saindo...")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        sys.exit(1)
