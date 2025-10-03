# cadastro/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # URLs públicas
        public_urls = [
            reverse('cadastro:login'), 
            '/admin/', 
            '/logout/',
            '/login/'
        ]
        
        if request.path in public_urls or request.user.is_anonymous:
            return None
        
        # Controle de acesso por tipo de usuário
        if hasattr(request.user, 'tipo_acesso'):
            # Operadores só acessam cadastro
            if (request.user.tipo_acesso == 'operador' and 
                not request.path.startswith('/cadastro/') and
                not request.path.startswith('/meu-perfil/')):
                return redirect('cadastro:cadastrar_cliente')
            
            # Responsáveis e Admins podem acessar gestão de usuários
            if (request.path.startswith('/admin/usuarios/') and 
                request.user.tipo_acesso not in ['admin', 'responsavel']):
                return redirect('cadastro:acesso_negado')
        
        return None