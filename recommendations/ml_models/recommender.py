import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import os
from django.conf import settings

class HybridRecommender:
    def __init__(self):
        self.content_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.svd = None  # Inicializar como None
        self.is_trained = False
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'trained_model')
        
    def prepare_product_features(self, products):
        """Prepara features dos produtos para content-based filtering"""
        product_features = []
        product_ids = []
        
        for product in products:
            # Combina nome, descrição e categoria para criar features de texto
            text_features = f'{product.name} {product.description} {product.category}'
            product_features.append(text_features)
            product_ids.append(product.id)
            
        return product_features, product_ids
    
    def create_user_product_matrix(self, interactions):
        """Cria matriz usuario-produto para collaborative filtering"""
        if not interactions:
            return pd.DataFrame()
            
        # Converte interações para DataFrame
        data = []
        for interaction in interactions:
            data.append({
                'user_id': interaction.user.id,
                'product_id': interaction.product.id,
                'weight': self._get_interaction_weight(interaction.interaction_type)
            })
            
        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame()
            
        # Cria matriz usuario-produto
        user_product_matrix = df.pivot_table(
            index='user_id', 
            columns='product_id', 
            values='weight', 
            aggfunc='sum',
            fill_value=0
        )
        return user_product_matrix
    
    def _get_interaction_weight(self, interaction_type):
        """Define pesos para diferentes tipos de interação"""
        weights = {
            'view': 1,
            'click': 2, 
            'rating': 3,
            'purchase': 5
        }
        return weights.get(interaction_type, 1)
    
    def train(self, products, interactions):
        """Treina o modelo com dados atuais"""
        print("# Treinando modelo de recomendações...")
        
        # Content-based features
        product_features, product_ids = self.prepare_product_features(products)
        if product_features:
            self.content_matrix = self.content_vectorizer.fit_transform(product_features)
            self.product_ids = product_ids
            print(f"✅ Content-based: {len(product_features)} produtos processados")
        else:
            self.content_matrix = None
            print("⚠️  Content-based: Nenhum produto para treinar")
            
        # Collaborative filtering
        self.user_product_matrix = self.create_user_product_matrix(interactions)
        if not self.user_product_matrix.empty:
            n_users, n_products = self.user_product_matrix.shape
            print(f"✅ Collaborative: {n_users} usuários, {n_products} produtos")
            
            # Ajusta dinamicamente o número de componentes
            n_components = min(30, n_users - 1, n_products - 1)
            n_components = max(2, n_components)  # Mínimo de 2 componentes
            
            if n_components >= 2:
                self.svd = TruncatedSVD(n_components=n_components, n_iter=20, random_state=42)
                self.svd.fit(self.user_product_matrix)
                self.user_ids = list(self.user_product_matrix.index)
                print(f"✅ SVD treinado com {n_components} componentes")
            else:
                self.svd = None
                self.user_ids = list(self.user_product_matrix.index)
                print("⚠️  SVD: Dados insuficientes para treinar SVD")
        else:
            self.user_ids = []
            print("⚠️  Collaborative: Nenhuma interação para treinar")
            
        self.is_trained = True
        print("# ✅ Modelo treinado com sucesso!")
        return True
    
    def recommend_for_user(self, user, products, top_n=10):
        """Gera recomendações para um usuário específico"""
        if not self.is_trained:
            print("⚠️  Modelo não treinado, usando fallback")
            return self._get_fallback_recommendations(products, top_n)
            
        # Import aqui para evitar circular imports
        from recommendations.models import UserInteraction
        
        user_interactions = UserInteraction.objects.filter(user=user)
        
        if user_interactions.count() < 3:
            # Se usuário tem poucas interações, use content-based + popularidade
            print(f"🔍 Usuário {user.id} tem poucas interações, usando método híbrido")
            return self._get_hybrid_recommendations(user, products, top_n)
        else:
            # Se usuário tem interações, use collaborative filtering
            print(f"🔍 Usuário {user.id} tem interações, usando collaborative filtering")
            return self._get_collaborative_recommendations(user, products, top_n)
    
    def _get_hybrid_recommendations(self, user, products, top_n):
        """Recomendações híbridas para novos usuários"""
        try:
            # Import aqui para evitar circular imports
            from recommendations.models import UserInteraction
            
            # Content-based similarity
            if self.content_matrix is not None and hasattr(self, 'product_ids'):
                content_sim = cosine_similarity(self.content_matrix)
                
                # Pega produtos que o usuário já interagiu
                user_interactions = UserInteraction.objects.filter(user=user)
                interacted_product_ids = [interaction.product.id for interaction in user_interactions]
                
                if interacted_product_ids:
                    # Baseado nos produtos que usuário já viu
                    product_indices = []
                    for pid in interacted_product_ids:
                        if pid in self.product_ids:
                            product_indices.append(self.product_ids.index(pid))
                    
                    if product_indices:
                        scores = np.mean(content_sim[product_indices], axis=0)
                        print(f"✅ Hybrid: Baseado em {len(product_indices)} produtos interagidos")
                    else:
                        scores = np.random.rand(len(products)) * 0.5
                        print("⚠️  Hybrid: Nenhum produto interagido encontrado na matriz")
                else:
                    # Se não tem interações, use diversidade
                    scores = np.random.rand(len(products)) * 0.5
                    print("⚠️  Hybrid: Nenhuma interação, usando diversidade")
            else:
                scores = np.random.rand(len(products))
                print("⚠️  Hybrid: Matriz de conteúdo não disponível")
                
            # Adiciona um pouco de aleatoriedade para diversidade
            diversity_boost = np.random.rand(len(products)) * 0.3
            final_scores = scores + diversity_boost
            
            # Ordena por score
            product_scores = list(zip(products, final_scores))
            product_scores.sort(key=lambda x: x[1], reverse=True)
            
            recommendations = [product for product, score in product_scores[:top_n]]
            print(f"✅ Hybrid: {len(recommendations)} recomendações geradas")
            return recommendations
            
        except Exception as e:
            print(f"❌ Erro em recomendações híbridas: {e}")
            return self._get_fallback_recommendations(products, top_n)
    
    def _get_collaborative_recommendations(self, user, products, top_n):
        """Recomendações baseadas em collaborative filtering"""
        try:
            # Import aqui para evitar circular imports
            from recommendations.models import UserInteraction
            
            if (not hasattr(self, 'user_ids') or 
                user.id not in self.user_ids or 
                self.user_product_matrix.empty or
                self.svd is None):
                print("⚠️  Collaborative: Condições não atendidas, usando hybrid")
                return self._get_hybrid_recommendations(user, products, top_n)
                
            user_idx = self.user_ids.index(user.id)
            user_vector = self.user_product_matrix.iloc[user_idx:user_idx+1]
            
            # Transforma para espaço latente
            user_latent = self.svd.transform(user_vector)
            
            # Calcula similaridade com outros usuários
            all_user_latent = self.svd.transform(self.user_product_matrix)
            user_similarity = cosine_similarity(user_latent, all_user_latent)[0]
            
            # Recomenda produtos que usuários similares gostaram
            similar_users_idx = np.argsort(user_similarity)[-10:]  # Top 10 usuários similares
            
            recommended_products = set()
            for idx in similar_users_idx:
                similar_user_id = self.user_ids[idx]
                user_interactions = UserInteraction.objects.filter(user_id=similar_user_id)
                
                for interaction in user_interactions:
                    if interaction.product_id not in [p.id for p in products]:
                        continue
                    recommended_products.add(interaction.product_id)
                    if len(recommended_products) >= top_n * 2:
                        break
                if len(recommended_products) >= top_n * 2:
                    break
                    
            # Converte para objetos de produto
            recommended_products = list(recommended_products)[:top_n]
            product_map = {p.id: p for p in products}
            recommendations = [product_map[pid] for pid in recommended_products if pid in product_map]
            
            print(f"✅ Collaborative: {len(recommendations)} recomendações geradas")
            return recommendations
            
        except Exception as e:
            print(f"❌ Erro em collaborative filtering: {e}")
            return self._get_fallback_recommendations(products, top_n)
    
    def _get_fallback_recommendations(self, products, top_n):
        """Recomendações de fallback baseadas em popularidade"""
        if not products:
            return []
            
        # Import aqui para evitar circular imports
        from recommendations.models import UserInteraction
        
        # Simula popularidade baseada em interações
        popular_products = []
        for product in products:
            interaction_count = UserInteraction.objects.filter(product=product).count()
            popular_products.append((product, interaction_count))
            
        # Ordena por popularidade
        popular_products.sort(key=lambda x: x[1], reverse=True)
        
        # Se não há interações, retorna aleatório
        if all(count == 0 for product, count in popular_products):
            return list(products)[:top_n]
            
        recommendations = [product for product, count in popular_products[:top_n]]
        print(f"✅ Fallback: {len(recommendations)} recomendações por popularidade")
        return recommendations

# Instância global do recomendador
recommender = HybridRecommender()