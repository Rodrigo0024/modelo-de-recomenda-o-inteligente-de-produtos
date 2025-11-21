import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random

class SimpleRecommender:
    def __init__(self):
        self.content_vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        self.is_trained = False
        
    def prepare_product_features(self, products):
        """Prepara features dos produtos para content-based filtering"""
        product_features = []
        product_ids = []
        
        for product in products:
            # Combina nome, descrição e categoria
            text_features = f"{product.name} {product.description} {product.category}"
            product_features.append(text_features)
            product_ids.append(product.id)
            
        return product_features, product_ids
    
    def train(self, products, interactions):
        """Treina o modelo simplificado"""
        print("🔄 Treinando modelo simplificado de recomendações...")
        
        # Content-based features apenas
        product_features, product_ids = self.prepare_product_features(products)
        
        if product_features:
            self.content_matrix = self.content_vectorizer.fit_transform(product_features)
            self.product_ids = product_ids
        else:
            self.content_matrix = None
            
        self.is_trained = True
        print("✅ Modelo simplificado treinado com sucesso!")
        return True
    
    def recommend_for_user(self, user, products, top_n=6):
        """Recomendações simplificadas baseadas em conteúdo"""
        if not self.is_trained or not hasattr(self, 'content_matrix') or self.content_matrix is None:
            return self._get_random_recommendations(products, top_n)
            
        try:
            # Import aqui para evitar circular imports
            from ..models import UserInteraction
            
            # Calcula similaridade entre produtos
            content_sim = cosine_similarity(self.content_matrix)
            
            # Pega produtos que o usuário já interagiu
            user_interactions = UserInteraction.objects.filter(user=user)
            interacted_product_ids = [interaction.product_id for interaction in user_interactions]
            
            if interacted_product_ids:
                # Baseado nos produtos que usuário já viu
                scores = np.mean(content_sim[[self.product_ids.index(pid) for pid in interacted_product_ids if pid in self.product_ids]], axis=0)
            else:
                # Se não tem interações, use produtos diversos
                scores = np.ones(len(products)) * 0.5
                
            # Adiciona diversidade
            diversity_boost = np.random.rand(len(products)) * 0.3
            final_scores = scores + diversity_boost
            
            # Ordena por score
            product_scores = list(zip(products, final_scores))
            product_scores.sort(key=lambda x: x[1], reverse=True)
            
            recommended = [product for product, score in product_scores[:top_n]]
            
            # Garante que temos recomendações suficientes
            if len(recommended) < top_n:
                remaining = [p for p in products if p not in recommended]
                recommended.extend(random.sample(remaining, min(top_n - len(recommended), len(remaining))))
            
            return recommended
            
        except Exception as e:
            print(f"❌ Erro em recomendações: {e}")
            return self._get_random_recommendations(products, top_n)
    
    def _get_random_recommendations(self, products, top_n):
        """Recomendações aleatórias de fallback"""
        if not products:
            return []
        return random.sample(list(products), min(top_n, len(products)))

# Instância global do recomendador
recommender = SimpleRecommender()