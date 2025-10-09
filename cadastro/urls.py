from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# Define o namespace do aplicativo
app_name = 'cadastro'

# Definição dos padrões de URL
urlpatterns = [
    # URLs de Autenticação
    path('login/', views.CustomLoginView.as_view(), name='login'),
    
    # ATUALIZADO: Agora aponta para a sua função 'views.logout_view'
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('acesso-negado/', views.acesso_negado, name='acesso_negado'),
    
    # URL raiz do app cadastro (Dashboard/Home)
    path('', views.home, name='home'),
    
    # URLs Principais do Sistema (Clientes e Exportação)
    path('cadastrar-cliente/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('exportar-dados/', views.exportar_dados, name='exportar_dados'),
    path('novos-clientes/', views.novos_clientes, name='novos_clientes'),
    
    # URLs de Gerenciamento de Usuários (Páginas)
    path('gerenciar-usuarios/', views.gerenciar_usuarios, name='gerenciar_usuarios'),
    path('listar-usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('criar-usuario/', views.criar_usuario, name='criar_usuario'),
    path('editar-usuario/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('redefinir-senha/<int:usuario_id>/', views.redefinir_senha, name='redefinir_senha'),
    # Rota para o perfil do usuário logado (que está dando erro de template)
    path('meu-perfil/', views.meu_perfil, name='meu_perfil'),
    
    # Operações de gerenciamento de usuários (Ações)
    path('usuarios/<int:usuario_id>/ativar-desativar/', views.ativar_desativar_usuario, name='ativar_desativar_usuario'),
    path('usuarios/<int:usuario_id>/alterar-tipo/', views.alterar_tipo_acesso, name='alterar_tipo_acesso'),
    path('usuarios/<int:usuario_id>/excluir/', views.excluir_usuario, name='excluir_usuario'),
    
    # APIs para AJAX/Fetch (Clientes)
    path('api/clientes/', views.lista_clientes, name='lista_clientes'),
    path('api/clientes/<int:cliente_id>/', views.detalhe_cliente, name='detalhe_cliente'),
    path('api/clientes/<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('api/clientes/<int:cliente_id>/excluir/', views.excluir_cliente, name='excluir_cliente'),
    path('api/validar-cliente/', views.validar_cliente, name='validar_cliente'),
]
