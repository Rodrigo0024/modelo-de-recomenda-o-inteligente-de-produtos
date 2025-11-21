from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404,  redirect 
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .models import Product, UserInteraction, Recommendation
from .ml_models.recommender import recommender
from django.db import models
from django.core.paginator import Paginator  # Adicione esta importação
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product, UserInteraction


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
            
            messages.success(request, f'✅ Modelo treinado com sucesso!')
            
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
# NOVAS VIEWS PARA SISTEMA DE NAVEGAÇÃO - ADAPTADAS PARA SEU MODELO
# ============================================================================
def product_explorer(request):
    """Página para explorar todos os produtos"""
    try:
        # Carrega TODOS os produtos do banco de dados
        all_products = Product.objects.all().order_by('-id')
        
        print(f"🎯 PRODUTOS ENCONTRADOS: {len(all_products)}")
        
        # Produtos populares (baseado em userinteraction - nome correto do campo)
        popular_products = Product.objects.annotate(
            interaction_count=Count('userinteraction')  # CORRIGIDO: 'userinteraction'
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
            'popular_products': all_products[:8],  # Fallback: primeiros 8 produtos
            'categories': Product.objects.values_list('category', flat=True).distinct(),
            'user_recommendations': None,
            'total_products': all_products.count(),
            'error': 'Erro ao carregar produtos populares'
        })
@login_required
def product_detail(request, product_id):
    """Página de detalhes do produto - VERSÃO CORRIGIDA"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        print(f"🔍 DETALHES DO PRODUTO: {product.name} | Usuário: {request.user}")
        
        # Registrar visualização
        if request.user.is_authenticated:
            try:
                interaction, created = UserInteraction.objects.update_or_create(
                    user=request.user,
                    product=product,
                    interaction_type='view',
                    defaults={'timestamp': timezone.now()}
                )
                if created:
                    print(f"✅ NOVA VISUALIZAÇÃO REGISTRADA: {product.name}")
            except Exception as e:
                print(f"❌ ERRO AO REGISTRAR VISUALIZAÇÃO: {e}")
        
        # Produtos da mesma categoria
        same_category_products = []
        if product.category and product.category.strip():  # Verifica se não está vazio
            same_category_products = Product.objects.filter(
                category=product.category
            ).exclude(id=product.id).order_by('?')[:4]
        
        # Características
        features_list = []
        if product.features and isinstance(product.features, str):
            features_list = [feature.strip() for feature in product.features.split(',')]
        
        # Estatísticas - CÁLCULO CORRETO
        view_count = product.userinteraction_set.filter(interaction_type='view').count()
        wishlist_count = product.userinteraction_set.filter(interaction_type='wishlist').count()
        
        # Calcular avaliação média CORRETAMENTE
        ratings = product.userinteraction_set.filter(
            interaction_type='rating'
        ).exclude(rating__isnull=True).values_list('rating', flat=True)
        
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # ⭐⭐ VERIFICAR AVALIAÇÃO DO USUÁRIO ATUAL - CORRIGIDA ⭐⭐
        user_rating = None
        if request.user.is_authenticated:
            try:
                # Primeiro tenta pegar uma única avaliação
                user_interaction = UserInteraction.objects.get(
                    user=request.user,
                    product=product,
                    interaction_type='rating'
                )
                user_rating = user_interaction.rating
                print(f"⭐ AVALIAÇÃO DO USUÁRIO ENCONTRADA: {user_rating} estrelas")
                
            except UserInteraction.DoesNotExist:
                user_rating = None
                print(f"⭐ USUÁRIO AINDA NÃO AVALIOU ESTE PRODUTO")
                
            except UserInteraction.MultipleObjectsReturned:
                # Se houver múltiplas avaliações, pega a mais recente
                print(f"⚠️ MÚLTIPLAS AVALIAÇÕES ENCONTRADAS, USANDO A MAIS RECENTE")
                user_interaction = UserInteraction.objects.filter(
                    user=request.user,
                    product=product,
                    interaction_type='rating'
                ).order_by('-timestamp').first()
                user_rating = user_interaction.rating if user_interaction else None
                print(f"⭐ AVALIAÇÃO MAIS RECENTE: {user_rating} estrelas")
        
        print(f"📊 ESTATÍSTICAS DO PRODUTO {product.name}:")
        print(f"   - Visualizações: {view_count}")
        print(f"   - Wishlist: {wishlist_count}")
        print(f"   - Avaliações: {len(ratings)} ratings")
        print(f"   - Média: {average_rating:.1f}")
        print(f"   - Avaliação do usuário: {user_rating}")
        print(f"   - Categoria: '{product.category}'")
        if ratings:
            print(f"   - Ratings individuais: {list(ratings)}")
        
        context = {
            'product': product,
            'same_category_products': same_category_products,
            'features_list': features_list,
            'view_count': view_count,
            'wishlist_count': wishlist_count,
            'average_rating': average_rating,
            'user_rating': user_rating,
        }
        
        return render(request, 'recommendations/product_detail.html', context)
        
    except Exception as e:
        print(f"❌ ERRO NA PÁGINA DE DETALHES DO PRODUTO: {e}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'recommendations/product_detail.html', {
            'error': 'Erro ao carregar detalhes do produto'
        })
@login_required
def category_products(request, category_name):
    """Página para filtrar produtos por categoria"""
    try:
        print(f"🔍 Buscando produtos da categoria: '{category_name}'")
        
        # DEBUG: Verificar todos os produtos e categorias
        all_products = Product.objects.all()
        print(f"📦 Total de produtos no banco: {all_products.count()}")
        
        all_categories = Product.objects.values_list('category', flat=True).distinct()
        print(f"📂 Categorias disponíveis no banco: {list(all_categories)}")
        
        # Mostrar produtos da categoria específica
        print(f"🎯 Produtos com categoria '{category_name}':")
        category_products_found = []
        for product in all_products:
            if product.category and category_name.lower() in product.category.lower():
                print(f"   ✅ {product.id}: {product.name} -> '{product.category}'")
                category_products_found.append(product)
        
        print(f"🎯 Total de produtos encontrados manualmente: {len(category_products_found)}")
        
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
            'categories': all_categories,
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
@login_required
def record_interaction(request):
    """API para registrar interações do usuário (AJAX)"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            product_id = request.POST.get('product_id')
            interaction_type = request.POST.get('interaction_type', 'click')
            rating = request.POST.get('rating')
            
            product = get_object_or_404(Product, id=product_id)
            
            # Cria a interação
            interaction_data = {
                'user': request.user,
                'product': product,
                'interaction_type': interaction_type,
            }
            
            # Adiciona rating se fornecido
            if rating and interaction_type == 'rating':
                interaction_data['rating'] = int(rating)
            
            interaction = UserInteraction.objects.create(**interaction_data)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Interação {interaction_type} registrada para {product.name}',
                'interaction_id': interaction.id
            })
            
        except Exception as e:
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
@login_required
@login_required
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
        
        # Produtos mais visualizados - USANDO COUNT IMPORTADO CORRETAMENTE
        from django.db.models import Count
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
                if stat['product__category']:  # Só adicionar se categoria não for vazia
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
            'category_stats': category_stats[:5],  # Top 5 categorias
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
                    interaction_type='rating',  # Tipo específico para avaliação
                    defaults={
                        'rating': int(rating),
                        'timestamp': timezone.now()  # Atualiza o timestamp
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
        print(f"  - Produto: {interaction.product.name} | Tipo: {interaction.interaction_type} | Rating: {interaction.rating} | Data: {interaction.created_at}")
    
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


@login_required
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
                
                # DEBUG: Verificar todas as avaliações deste produto
                all_ratings = UserInteraction.objects.filter(
                    product=product, 
                    interaction_type='rating'
                ).exclude(rating__isnull=True)
                print(f"📊 TOTAL DE AVALIAÇÕES PARA ESTE PRODUTO: {all_ratings.count()}")
                for r in all_ratings:
                    print(f"   - Usuário: {r.user.username}, Rating: {r.rating}")
                
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

