import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.conf import settings
from django.db import models

from .models import Product, UserInteraction, Recommendation
from .ml_models.recommender import recommender
from .ai_generator import AIGenerator

# ✅ Crie a instância aqui mesmo
ai_generator = AIGenerator()

# ============================================================================
# VIEWS PRINCIPAIS
# ============================================================================

def home(request):
    """Página inicial"""
    return render(request, 'recommendations/home.html')

def index(request):
    """Página principal alternativa"""
    return render(request, 'recommendations/index.html')

@login_required
def train_recommender(request):
    """View para treinar o modelo com template bonito"""
    if request.method == 'POST':
        try:
            products = Product.objects.all()
            interactions = UserInteraction.objects.all()
            
            # Treina o modelo
            success = recommender.train(products, interactions)
            
            # Estatísticas para mostrar no template
            stats = {
                'products_count': products.count(),
                'interactions_count': interactions.count(),
                'users_count': UserInteraction.objects.values('user').distinct().count(),
                'trained_at': timezone.now(),
                'training_success': success,
            }
            
            messages.success(request, '✅ Modelo treinado com sucesso!')
            
            # Renderiza a página com os resultados
            return render(request, 'recommendations/training_results.html', {
                'stats': stats,
                'success': True
            })
            
        except Exception as e:
            messages.error(request, f'❌ Erro ao treinar modelo: {str(e)}')
            return render(request, 'recommendations/training_results.html', {
                'success': False,
                'error': str(e)
            })
    
    # Se for GET, mostra a página de treinamento
    stats = {
        'total_products': Product.objects.count(),
        'total_interactions': UserInteraction.objects.count(),
        'unique_users': UserInteraction.objects.values('user').distinct().count(),
    }
    
    return render(request, 'recommendations/train_model.html', {
        'stats': stats
    })

@login_required
def get_recommendations(request):
    """View para obter recomendações para o usuário logado"""
    try:
        user = request.user
        products = Product.objects.all()
        recommendations = recommender.recommend_for_user(user, products, top_n=10)
        
        recommended_data = [
            {
                'id': p.id, 
                'name': p.name, 
                'category': p.category,
                'price': str(p.price),
                'image_url': p.image_url
            } for p in recommendations
        ]
        
        return JsonResponse({
            'status': 'success', 
            'recommendations': recommended_data
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def user_recommendations(request):
    """View para página de recomendações"""
    return render(request, 'recommendations/recommendations.html')

@login_required
def model_status(request):
    """Mostra o status atual do modelo"""
    status_info = {
        'is_trained': recommender.is_trained,
        'training_time': getattr(recommender, 'last_trained', 'Nunca'),
        'products_in_model': len(getattr(recommender, 'product_ids', [])),
        'users_in_model': len(getattr(recommender, 'user_ids', [])),
    }
    
    # Estatísticas simples do banco
    stats = {
        'total_products': Product.objects.count(),
        'total_interactions': UserInteraction.objects.count(),
    }
    
    return render(request, 'recommendations/model_status.html', {
        'status': status_info,
        'stats': stats
    })

# ============================================================================
# SISTEMA DE NAVEGAÇÃO
# ============================================================================

def product_explorer(request):
    """Página para explorar todos os produtos"""
    try:
        # Carrega TODOS os produtos do banco de dados
        all_products = Product.objects.all().order_by('-id')
        
        print(f"🎯 PRODUTOS ENCONTRADOS: {len(all_products)}")
        
        # Produtos populares
        popular_products = Product.objects.annotate(
            interaction_count=Count('userinteraction')
        ).order_by('-interaction_count')[:8]
        
        # Categorias disponíveis
        categories = Product.objects.values_list('category', flat=True).distinct()
        
        # Tenta carregar recomendações do usuário (se existirem)
        user_recommendations = None
        if request.user.is_authenticated:
            try:
                user_recommendations = get_user_recommendations(request.user.id)
                if user_recommendations and len(user_recommendations) > 0:
                    user_recommendations = user_recommendations[:6]
            except Exception as e:
                print(f"Erro ao carregar recomendações: {e}")
                user_recommendations = None
        
        context = {
            'products': all_products,
            'popular_products': popular_products,
            'categories': categories,
            'user_recommendations': user_recommendations,
            'total_products': all_products.count(),
        }
        
        print(f"✅ Contexto enviado: {len(all_products)} produtos, {len(popular_products)} populares")
        return render(request, 'recommendations/product_explorer.html', context)
        
    except Exception as e:
        print(f"❌ Erro na página de explorar produtos: {e}")
        
        # Fallback seguro sem usar annotate
        all_products = Product.objects.all().order_by('-id')
        
        return render(request, 'recommendations/product_explorer.html', {
            'products': all_products,
            'popular_products': all_products[:8],
            'categories': Product.objects.values_list('category', flat=True).distinct(),
            'user_recommendations': None,
            'total_products': all_products.count(),
            'error': 'Erro ao carregar produtos populares'
        })

def get_user_recommendations(user_id, limit=6):
    """Função auxiliar para obter recomendações do usuário"""
    try:
        # Implemente sua lógica de recomendação aqui
        # Por enquanto, retorna produtos populares como fallback
        return Product.objects.annotate(
            interaction_count=Count('userinteraction')
        ).order_by('-interaction_count')[:limit]
    except Exception:
        return Product.objects.all()[:limit]
@login_required
def product_detail(request, product_id):
    """Página de detalhes do produto - VERSÃO CORRIGIDA"""
    try:
        print(f"🔍 ACESSANDO PRODUCT_DETAIL - ID: {product_id}, Usuário: {request.user}")
        
        # ✅ VALIDAÇÃO do product_id
        if not product_id:
            print("❌ ID DO PRODUTO VAZIO")
            messages.error(request, "ID do produto não fornecido.")
            return redirect('/')
        
        try:
            product_id = int(product_id)
        except (ValueError, TypeError):
            print(f"❌ ID DO PRODUTO INVÁLIDO: {product_id}")
            messages.error(request, "ID do produto inválido.")
            return redirect('/')
        
        if product_id <= 0:
            print(f"❌ ID DO PRODUTO INVÁLIDO: {product_id}")
            messages.error(request, "ID do produto inválido.")
            return redirect('/')
        
        # ✅ Buscar produto principal
        try:
            product = Product.objects.get(id=product_id)
            print(f"✅ PRODUTO ENCONTRADO: {product.name} (ID: {product.id})")
        except Product.DoesNotExist:
            print(f"❌ PRODUTO NÃO ENCONTRADO: {product_id}")
            messages.error(request, "Produto não encontrado.")
            return redirect('/')
        
        # ✅ PRODUTOS RELACIONADOS - COM VALIDAÇÃO ROBUSTA
        same_category_products = []
        if product.category and product.category.strip():
            try:
                # Busca produtos da mesma categoria
                category_products = Product.objects.filter(
                    category=product.category
                ).exclude(id=product.id).order_by('?')[:8]  # Pega mais para filtrar depois
                
                # ✅ FILTRA APENAS PRODUTOS VÁLIDOS
                valid_related_products = []
                for related_product in category_products:
                    if (related_product and 
                        related_product.id and 
                        related_product.id > 0 and 
                        related_product != product):
                        valid_related_products.append(related_product)
                
                # Limita a 4 produtos válidos
                same_category_products = valid_related_products[:4]
                print(f"✅ PRODUTOS RELACIONADOS: {len(same_category_products)} válidos encontrados")
                
            except Exception as e:
                print(f"⚠️ ERRO AO BUSCAR PRODUTOS RELACIONADOS: {e}")
                same_category_products = []  # Lista vazia em caso de erro
        
        # ✅ Características
        features_list = []
        if product.features and isinstance(product.features, str):
            features_list = [feature.strip() for feature in product.features.split(',') if feature.strip()]
        
        # ✅ Estatísticas
        view_count = product.userinteraction_set.filter(interaction_type='view').count()
        wishlist_count = product.userinteraction_set.filter(interaction_type='wishlist').count()
        
        ratings = product.userinteraction_set.filter(
            interaction_type='rating'
        ).exclude(rating__isnull=True).values_list('rating', flat=True)
        
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # ✅ Avaliação do usuário atual
        user_rating = None
        if request.user.is_authenticated:
            try:
                user_interaction = UserInteraction.objects.filter(
                    user=request.user,
                    product=product,
                    interaction_type='rating'
                ).order_by('-timestamp').first()
                user_rating = user_interaction.rating if user_interaction else None
            except Exception as e:
                print(f"⚠️ ERRO AO BUSCAR AVALIAÇÃO: {e}")
                user_rating = None
        
        context = {
            'product': product,
            'same_category_products': same_category_products,  # ✅ AGORA SÓ PRODUTOS VÁLIDOS
            'features_list': features_list,
            'view_count': view_count,
            'wishlist_count': wishlist_count,
            'average_rating': round(average_rating, 1),
            'user_rating': user_rating,
        }
        
        return render(request, 'recommendations/product_detail.html', context)
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, "Erro ao carregar detalhes do produto.")
        return redirect('/')
@login_required
def category_products(request, category_name):
    """Página para filtrar produtos por categoria"""
    try:
        print(f"🔍 Buscando produtos da categoria: '{category_name}'")
        
        # Filtra produtos pela categoria (busca case-insensitive e parcial)
        category_products = Product.objects.filter(
            models.Q(category__iexact=category_name) |
            models.Q(category__icontains=category_name)
        ).distinct()
        
        print(f"📊 Produtos encontrados na query: {category_products.count()}")
        
        # Se não encontrar nada, mostrar todos os produtos como fallback
        if category_products.count() == 0:
            print("⚠️ Nenhum produto encontrado na categoria, mostrando todos os produtos")
            category_products = Product.objects.all()
            show_all_message = True
        else:
            show_all_message = False
        
        # Aplica busca se existir
        search_query = request.GET.get('search', '')
        if search_query:
            category_products = category_products.filter(
                models.Q(name__icontains=search_query) |
                models.Q(description__icontains=search_query)
            )
        
        # Aplica ordenação
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'price_low':
            category_products = category_products.order_by('price')
        elif sort_by == 'price_high':
            category_products = category_products.order_by('-price')
        elif sort_by == 'name':
            category_products = category_products.order_by('name')
        elif sort_by == 'popular':
            category_products = category_products.annotate(
                view_count=models.Count('userinteraction')
            ).order_by('-view_count')
        else:  # newest
            category_products = category_products.order_by('-id')
        
        # Paginação
        paginator = Paginator(category_products, 12)
        page_number = request.GET.get('page')
        products_page = paginator.get_page(page_number)
        
        # Estatísticas
        total_products = category_products.count()
        
        # Calcular visualizações totais
        if category_products.exists():
            total_views = UserInteraction.objects.filter(
                product__in=category_products,
                interaction_type='view'
            ).count()
            average_price = category_products.aggregate(avg_price=models.Avg('price'))['avg_price'] or 0
        else:
            total_views = 0
            average_price = 0
        
        context = {
            'products': products_page,
            'category_name': category_name,
            'categories': Product.objects.values_list('category', flat=True).distinct(),
            'total_products': total_products,
            'total_views': total_views,
            'average_price': average_price,
            'search_query': search_query,
            'sort_by': sort_by,
            'show_all_message': show_all_message,
        }
        
        print(f"✅ Contexto enviado: {products_page.paginator.count} produtos")
        return render(request, 'recommendations/category_products.html', context)
        
    except Exception as e:
        print(f"❌ Erro CRÍTICO na página de categoria: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback seguro - mostrar apenas produtos da categoria manualmente
        all_products = Product.objects.all()
        category_products_fallback = []
        for product in all_products:
            if product.category and category_name.lower() in product.category.lower():
                category_products_fallback.append(product)
        
        # Se não encontrar nenhum, mostrar todos
        if not category_products_fallback:
            category_products_fallback = all_products[:12]
        
        all_categories = Product.objects.values_list('category', flat=True).distinct()
        
        return render(request, 'recommendations/category_products.html', {
            'products': category_products_fallback,
            'category_name': category_name,
            'categories': all_categories,
            'total_products': len(category_products_fallback),
            'total_views': 0,
            'average_price': 0,
            'error': f'Erro ao carregar produtos: {str(e)}'
        })

# ============================================================================
# APIs DE INTERAÇÃO
# ============================================================================

@login_required
def record_interaction_api(request):
    """API para registrar interações do usuário (AJAX) - VERSÃO COM MAIS LOGS"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            product_id = request.POST.get('product_id')
            interaction_type = request.POST.get('interaction_type', 'view')
            rating = request.POST.get('rating')
            
            print(f"🔍 REGISTRANDO INTERAÇÃO - Produto: {product_id}, Tipo: {interaction_type}, Rating: {rating}")
            
            product = get_object_or_404(Product, id=product_id)
            
            # Dados para a interação
            interaction_data = {
                'user': request.user,
                'product': product,
                'interaction_type': interaction_type,
                'timestamp': timezone.now()
            }
            
            # Adiciona rating se fornecido
            if rating and interaction_type == 'rating':
                interaction_data['rating'] = int(rating)
                print(f"⭐ REGISTRANDO AVALIAÇÃO: {rating} estrelas para {product.name}")
            
            # Para avaliações, usar update_or_create
            if interaction_type == 'rating':
                interaction, created = UserInteraction.objects.update_or_create(
                    user=request.user,
                    product=product,
                    interaction_type='rating',
                    defaults=interaction_data
                )
                action = "criada" if created else "atualizada"
                print(f"✅ AVALIAÇÃO {action}: {rating} estrelas para {product.name}")
                
            else:
                interaction = UserInteraction.objects.create(**interaction_data)
                print(f"✅ INTERAÇÃO criada: {interaction_type} para {product.name}")
            
            return JsonResponse({
                'status': 'success',
                'message': f'Interação {interaction_type} registrada para {product.name}',
                'interaction_id': interaction.id
            })
            
        except Exception as e:
            print(f"❌ ERRO AO REGISTRAR INTERAÇÃO: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def get_recommendations_ajax(request):
    """API para obter recomendações atualizadas (AJAX)"""
    try:
        products = Product.objects.all()
        recommendations = recommender.recommend_for_user(
            request.user, 
            products, 
            top_n=12
        )
        
        recommended_data = [
            {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': str(p.price),
                'description': p.description[:100] + '...' if len(p.description) > 100 else p.description,
                'image_url': p.image_url or '/static/images/default-product.jpg'
            } for p in recommendations
        ]
        
        return JsonResponse({
            'status': 'success',
            'recommendations': recommended_data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def product_stats_api(request, product_id):
    """API para obter estatísticas atualizadas do produto"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Calcular estatísticas em tempo real
        view_count = product.userinteraction_set.filter(interaction_type='view').count()
        wishlist_count = product.userinteraction_set.filter(interaction_type='wishlist').count()
        
        ratings = product.userinteraction_set.filter(
            interaction_type='rating'
        ).exclude(rating__isnull=True).values_list('rating', flat=True)
        
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        return JsonResponse({
            'status': 'success',
            'view_count': view_count,
            'wishlist_count': wishlist_count,
            'average_rating': round(average_rating, 1),
            'rating_count': len(ratings)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

# ============================================================================
# DASHBOARD E AVALIAÇÕES
# ============================================================================

@login_required
def user_dashboard(request):
    """Dashboard do usuário com estatísticas e atividades - VERSÃO FINAL CORRIGIDA"""
    try:
        user = request.user
        print(f"🔍 CARREGANDO DASHBOARD PARA: {user.username}")
        
        # Buscar TODAS as interações do usuário
        user_interactions = UserInteraction.objects.filter(user=user)
        print(f"🔍 TOTAL DE INTERAÇÕES NO BANCO: {user_interactions.count()}")
        
        # Contar por tipo de forma explícita
        total_views = user_interactions.filter(interaction_type='view').count()
        wishlist_count = user_interactions.filter(interaction_type='wishlist').count()
        ratings_count = user_interactions.filter(interaction_type='rating').count()
        total_interactions = user_interactions.count()
        
        print(f"🔍 ESTATÍSTICAS - Views: {total_views}, Wishlist: {wishlist_count}, Ratings: {ratings_count}, Total: {total_interactions}")
        
        # Interações recentes - USAR TIMESTAMP
        recent_interactions = user_interactions.select_related('product').order_by('-timestamp')[:10]
        print(f"🔍 INTERAÇÕES RECENTES: {recent_interactions.count()}")
        
        # Produtos mais visualizados
        most_viewed_products = Product.objects.filter(
            userinteraction__user=user,
            userinteraction__interaction_type='view'
        ).annotate(
            view_count=Count('userinteraction')
        ).order_by('-view_count')[:4]
        
        print(f"🔍 PRODUTOS MAIS VISTOS: {most_viewed_products.count()}")
        
        # Estatísticas por categoria
        category_stats = []
        try:
            # Buscar categorias com as quais o usuário interagiu
            category_stats = user_interactions.values(
                'product__category'
            ).annotate(
                view_count=Count('id', filter=models.Q(interaction_type='view')),
                wishlist_count=Count('id', filter=models.Q(interaction_type='wishlist')),
                rating_count=Count('id', filter=models.Q(interaction_type='rating')),
            ).exclude(product__category__isnull=True).exclude(product__category='')
            
            # Formatar para o template
            formatted_stats = []
            for stat in category_stats:
                if stat['product__category']:
                    formatted_stats.append({
                        'category': stat['product__category'],
                        'view_count': stat['view_count'] or 0,
                        'wishlist_count': stat['wishlist_count'] or 0,
                        'rating_count': stat['rating_count'] or 0,
                    })
            
            category_stats = formatted_stats
            print(f"🔍 ESTATÍSTICAS POR CATEGORIA: {len(category_stats)}")
            
        except Exception as e:
            print(f"❌ Erro em category_stats: {e}")
            category_stats = []
        
        # Status do modelo
        try:
            # Verificar se existem recomendações para o usuário
            user_recommendations = Recommendation.objects.filter(user=user)
            model_trained = user_recommendations.exists()
            print(f"🔍 RECOMENDAÇÕES ENCONTRADAS: {user_recommendations.count()}")
        except Exception as e:
            print(f"❌ Erro ao verificar recomendações: {e}")
            user_recommendations = None
            model_trained = False
        
        context = {
            'total_views': total_views,
            'wishlist_count': wishlist_count,
            'ratings_count': ratings_count,
            'total_interactions': total_interactions,
            'recent_interactions': recent_interactions,
            'most_viewed_products': most_viewed_products,
            'category_stats': category_stats[:5],
            'user_recommendations': user_recommendations,
            'model_trained': model_trained,
        }
        
        print(f"✅ DASHBOARD PRONTO - Enviando contexto com {total_interactions} interações")
        return render(request, 'recommendations/user_dashboard.html', context)
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO DASHBOARD: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback com dados mínimos
        return render(request, 'recommendations/user_dashboard.html', {
            'total_views': 0,
            'wishlist_count': 0,
            'ratings_count': 0,
            'total_interactions': 0,
            'recent_interactions': [],
            'most_viewed_products': [],
            'category_stats': [],
            'model_trained': False,
            'error': f'Erro ao carregar dashboard: {str(e)}'
        })

@login_required
def rate_product(request, product_id):
    """View para avaliar um produto - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            rating = request.POST.get('rating')
            
            print(f"🔍 TENTANDO REGISTRAR AVALIAÇÃO - Produto: {product.name}, Rating: {rating}, Usuário: {request.user}")
            
            if rating and 1 <= int(rating) <= 5:
                # Cria ou atualiza a avaliação - CORRIGIDO
                interaction, created = UserInteraction.objects.update_or_create(
                    user=request.user,
                    product=product,
                    interaction_type='rating',
                    defaults={
                        'rating': int(rating),
                        'timestamp': timezone.now()
                    }
                )
                
                action = "criada" if created else "atualizada"
                print(f"✅ AVALIAÇÃO {action}: {rating} estrelas para {product.name}")
                messages.success(request, f'✅ Avaliação de {rating} estrelas {action} para {product.name}!')
            else:
                print(f"❌ RATING INVÁLIDO: {rating}")
                messages.error(request, '❌ Avaliação deve ser entre 1 e 5 estrelas.')
                
        except Exception as e:
            print(f"❌ ERRO AO REGISTRAR AVALIAÇÃO: {e}")
            messages.error(request, f'❌ Erro ao registrar avaliação: {str(e)}')
    
    return redirect('product_detail', product_id=product_id)

@login_required
def debug_interactions(request):
    """View para debug - ver todas as interações do usuário"""
    user_interactions = UserInteraction.objects.filter(user=request.user).select_related('product')
    
    print(f"🔍 DEBUG - Usuário: {request.user}")
    print(f"🔍 DEBUG - Total de interações: {user_interactions.count()}")
    
    for interaction in user_interactions:
        print(f"  - Produto: {interaction.product.name} | Tipo: {interaction.interaction_type} | Rating: {interaction.rating} | Data: {interaction.timestamp}")
    
    context = {
        'interactions': user_interactions,
        'total_count': user_interactions.count(),
    }
    return render(request, 'recommendations/debug_interactions.html', context)

@login_required
def test_interaction(request, product_id):
    """View para testar criação de interação"""
    product = get_object_or_404(Product, id=product_id)
    
    # Criar uma interação de teste
    interaction = UserInteraction.objects.create(
        user=request.user,
        product=product,
        interaction_type='view'
    )
    
    messages.success(request, f'✅ Interação de teste criada para {product.name}! ID: {interaction.id}')
    return redirect('debug_interactions')

# ============================================================================
# IA GENERATIVA - VIEWS CORRIGIDAS
# ============================================================================

@login_required
def ai_status(request):
    """Página para verificar o status da IA"""
    context = {
        'api_configured': ai_generator._is_configured(),
        'api_key': settings.DEEPSEEK_API_KEY,
        'api_key_preview': f"{settings.DEEPSEEK_API_KEY[:10]}..." if settings.DEEPSEEK_API_KEY else "Não configurada",
        'model': ai_generator.model,
        'provider': getattr(settings, 'AI_PROVIDER', 'deepseek')
    }
    
    return render(request, 'recommendations/ai_status.html', context)

@login_required
def generate_description_page(request):
    """Página para gerar descrições com IA - VERSÃO COMPLETA"""
    # Obter produtos para seleção
    products = Product.objects.all().order_by('name')[:50]
    categories = Product.objects.values_list('category', flat=True).distinct()
    
    # Estatísticas da IA
    ai_configured = ai_generator._is_configured()
    api_status = "✅ Configurada" if ai_configured else "❌ Não configurada"
    
    context = {
        'title': 'Gerar Descrição com IA',
        'products': products,
        'categories': categories,
        'ai_configured': ai_configured,
        'api_status': api_status,
        'model': ai_generator.model,
        'provider': getattr(settings, 'AI_PROVIDER', 'deepseek')
    }
    return render(request, 'recommendations/generate_description.html', context)

@login_required
def test_ai(request):
    """Página para testar a IA generativa - VERSÃO COMPLETA"""
    # Dados de exemplo para teste
    sample_products = [
        {
            'name': 'Smartphone Android 5G',
            'category': 'Eletrônicos',
            'price': '1299.99',
            'features': 'Tela 6.5", 128GB, Câmera Tripla, Bateria 5000mAh'
        },
        {
            'name': 'Livro de Ficção Científica',
            'category': 'Livros', 
            'price': '49.90',
            'features': 'Capa dura, 320 páginas, Edição limitada'
        },
        {
            'name': 'Fone de Ouvido Bluetooth',
            'category': 'Áudio',
            'price': '199.90',
            'features': 'Cancelamento de ruído, Bateria 30h, À prova dágua'
        }
    ]
    
    # Status da configuração
    ai_configured = ai_generator._is_configured()
    
    context = {
        'title': 'Testar IA Generativa',
        'sample_products': sample_products,
        'ai_configured': ai_configured,
        'api_key_preview': f"{settings.DEEPSEEK_API_KEY[:8]}..." if settings.DEEPSEEK_API_KEY else "Não configurada",
        'model': ai_generator.model,
        'max_tokens': ai_generator.max_tokens,
        'temperature': ai_generator.temperature
    }
    return render(request, 'recommendations/test_ai.html', context)

@login_required
def generate_description_api(request):
    """API para gerar descrição de produto com IA - VERSÃO FINAL"""
    print("🎯 API generate_description_api CHAMADA")
    
    if request.method == 'POST':
        try:
            print("📨 Recebendo dados POST...")
            
            # Verificar se há corpo na requisição
            if not request.body:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nenhum dado recebido'
                })
            
            # Carregar dados JSON
            data = json.loads(request.body)
            product_name = data.get('product_name', '').strip()
            category = data.get('category', '').strip()
            price = data.get('price', '0')
            features = data.get('features', '').strip()
            
            print(f"📦 Dados recebidos: {product_name}, {category}, {price}")
            
            if not product_name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nome do produto é obrigatório'
                })
            
            # Verificar se a IA está configurada
            if not ai_generator._is_configured():
                print("❌ IA não configurada")
                return JsonResponse({
                    'status': 'error',
                    'message': 'IA não configurada. Configure DEEPSEEK_API_KEY no arquivo .env'
                })
            
            print("🤖 Gerando descrição com IA...")
            
            # Gerar descrição com IA
            description = ai_generator.generate_product_description(
                product_name=product_name,
                category=category,
                price=price,
                features=features
            )
            
            print("✅ Descrição gerada com sucesso!")
            
            return JsonResponse({
                'status': 'success',
                'description': description,
                'product_name': product_name
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro JSON: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': 'Dados JSON inválidos'
            })
        except Exception as e:
            print(f"❌ Erro ao gerar descrição: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro interno: {str(e)}'
            })
    
    print("❌ Método não permitido")
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def test_ai_connection(request):
    """Testar conexão com a API de IA - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            # Teste simples
            test_response = ai_generator._call_deepseek_api("Responda apenas 'OK' se estiver funcionando.")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Conexão com IA estabelecida com sucesso!',
                'test_response': test_response,
                'api_configured': ai_generator._is_configured()
            })
            
        except Exception as e:
            print(f"❌ Erro no teste de conexão: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Falha na conexão: {str(e)}',
                'api_configured': ai_generator._is_configured()
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def generate_product_features(request):
    """View para gerar características de produto com IA - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            # Verificar se há corpo na requisição
            if not request.body:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nenhum dado recebido'
                })
            
            data = json.loads(request.body)
            product_name = data.get('product_name', '').strip()
            category = data.get('category', '').strip()
            
            print(f"🎯 GERANDO FEATURES IA - Produto: {product_name}")
            
            if not product_name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nome do produto é obrigatório'
                })
            
            # Verificar se a IA está configurada
            if not ai_generator._is_configured():
                return JsonResponse({
                    'status': 'error',
                    'message': 'IA não configurada'
                })
            
            features = ai_generator.generate_product_features(
                product_name=product_name,
                category=category
            )
            
            return JsonResponse({
                'status': 'success',
                'features': features
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Dados JSON inválidos'
            })
        except Exception as e:
            print(f"❌ Erro ao gerar features: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao gerar características: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})


@login_required
def ai_product_wizard(request):
    """Assistente completo para criação de produtos com IA - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            # Verificar se há corpo na requisição
            if not request.body:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nenhum dado recebido'
                })
            
            data = json.loads(request.body)
            product_name = data.get('product_name', '').strip()
            category = data.get('category', '').strip()
            price = data.get('price', '0')
            base_features = data.get('base_features', '').strip()
            
            print(f"🎯 INICIANDO WIZARD IA - Produto: {product_name}")
            
            if not product_name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nome do produto é obrigatório'
                })
            
            # Verificar se a IA está configurada
            if not ai_generator._is_configured():
                return JsonResponse({
                    'status': 'error',
                    'message': 'IA não configurada'
                })
            
            description = ai_generator.generate_product_description(
                product_name=product_name,
                category=category,
                price=price,
                features=base_features
            )
            
            enhanced_features = ai_generator.generate_product_features(
                product_name=product_name,
                category=category
            )
            
            # Combinar features
            all_features = base_features
            if base_features and enhanced_features:
                all_features = f"{base_features}, {enhanced_features}"
            elif enhanced_features:
                all_features = enhanced_features
            
            return JsonResponse({
                'status': 'success',
                'description': description,
                'features': all_features,
                'enhanced_features': enhanced_features
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Dados JSON inválidos'
            })
        except Exception as e:
            print(f"❌ Erro no wizard IA: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro no assistente: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})

@login_required
def get_product_data(request, product_id):
    """API para obter dados de um produto específico - VERSÃO CORRIGIDA"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        return JsonResponse({
            'status': 'success',
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'price': str(product.price),
                'features': product.features or '',
                'current_description': product.description or '',
                'image_url': product.image_url or ''
            }
        })
        
    except Exception as e:
        print(f"❌ Erro ao carregar produto: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao carregar produto: {str(e)}'
        })

@login_required
def bulk_generate_descriptions(request):
    """Gerar descrições em lote para produtos sem descrição - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            products_to_update = Product.objects.filter(
                Q(description__isnull=True) | 
                Q(description='')
            )[:2]  # Apenas 2 para teste
            
            results = []
            
            for product in products_to_update:
                try:
                    description = ai_generator.generate_product_description(
                        product_name=product.name,
                        category=product.category,
                        price=str(product.price),
                        features=product.features
                    )
                    
                    product.description = description
                    product.save()
                    
                    results.append({
                        'product': product.name,
                        'status': 'success',
                        'description_preview': description[:100] + '...'
                    })
                    
                except Exception as e:
                    results.append({
                        'product': product.name,
                        'status': 'error',
                        'error': str(e)
                    })
            
            return JsonResponse({
                'status': 'success',
                'message': f'Processados {len(results)} produtos',
                'results': results
            })
            
        except Exception as e:
            print(f"❌ Erro no processamento em lote: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro no processamento em lote: {str(e)}'
            })
    
    # GET - mostrar página
    products_needing_description = Product.objects.filter(
        Q(description__isnull=True) | 
        Q(description='')
    ).count()
    
    return render(request, 'recommendations/bulk_generate_descriptions.html', {
        'products_count': products_needing_description,
        'ai_configured': ai_generator._is_configured()
    })

@login_required
def update_product_description(request, product_id):
    """API para atualizar a descrição de um produto - VERSÃO CORRIGIDA"""
    print(f"🎯 API update_product_description CHAMADA para produto {product_id}")
    
    if request.method == 'POST':
        try:
            # Verificar se há corpo na requisição
            if not request.body:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nenhum dado recebido'
                })
            
            data = json.loads(request.body)
            new_description = data.get('description', '').strip()
            
            print(f"📝 Nova descrição: {new_description[:100]}...")
            
            product = get_object_or_404(Product, id=product_id)
            
            # Atualizar a descrição
            product.description = new_description
            product.save()
            
            # Registrar interação de geração de descrição
            UserInteraction.objects.create(
                user=request.user,
                product=product,
                interaction_type='ai_description_generated',
                timestamp=timezone.now()
            )
            
            print("✅ Descrição atualizada com sucesso!")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Descrição atualizada com sucesso!',
                'product_id': product_id
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro JSON: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': 'Dados JSON inválidos'
            })
        except Exception as e:
            print(f"❌ Erro ao atualizar descrição: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao atualizar descrição: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'})