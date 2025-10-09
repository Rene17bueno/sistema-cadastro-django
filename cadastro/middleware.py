from django.shortcuts import redirect
from django.urls import reverse

class AccessControlMiddleware:
    """
    Middleware para aplicar controle de acesso a nível de rota, complementando
    os decoradores de view. 
    
    Ele garante que:
    1. Usuários anônimos sejam redirecionados para o login.
    2. Operadores sejam estritamente restringidos às rotas de cadastro e perfil.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        # 1. Definição das URLs que são isentas (sempre permitidas, mesmo para anônimos)
        EXEMPT_URLS = [
            reverse('cadastro:login'), 
            reverse('cadastro:acesso_negado'),
            reverse('cadastro:logout'),
        ]

        # Obtém o caminho da URL (ignora query strings) e verifica a isenção.
        path = request.path_info.lstrip('/')
        # Verifica se o path começa com alguma das URLs isentas OU com 'admin/'
        is_exempt = any(path.startswith(url.lstrip('/')) for url in EXEMPT_URLS) or path.startswith('admin/')

        # 2. TRATAMENTO DE USUÁRIOS NÃO AUTENTICADOS
        if not request.user.is_authenticated and not is_exempt:
            # Redireciona anônimos tentando acessar rotas não isentas para o login.
            return redirect('cadastro:login')
        
        # 3. TRATAMENTO DE USUÁRIOS AUTENTICADOS (Controle de Acesso Fino)
        if request.user.is_authenticated and not is_exempt:
            
            # Restrição para OPERADORES:
            if hasattr(request.user, 'tipo_acesso') and request.user.tipo_acesso == 'operador':
                
                # Rotas que um operador PODE acessar.
                allowed_paths = [
                    '/cadastro/',      # Rota principal (cadastrar-cliente, exportar, APIs)
                    '/meu-perfil/',    # Rotas de perfil (meu_perfil, alterar_senha)
                    reverse('cadastro:home'), # A rota home (que redireciona para o cadastro)
                ]
                
                # Verifica se o path começa com alguma das rotas permitidas
                is_allowed = any(request.path_info.startswith(p) for p in allowed_paths)

                # Se o operador tentar acessar algo não permitido (ex: /admin/usuarios/), redireciona.
                if not is_allowed:
                    return redirect('cadastro:cadastrar_cliente')

        # Passa a requisição para a próxima camada (view) se tudo estiver ok.
        response = self.get_response(request)
        return response
