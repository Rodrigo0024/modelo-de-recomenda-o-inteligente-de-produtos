from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    category = models.CharField(max_length=100, verbose_name="Categoria")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    image_url = models.URLField(blank=True, null=True, verbose_name="URL da Imagem")
    
    # Características para o sistema de recomendação
    features = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class UserInteraction(models.Model):
    INTERACTION_TYPES = [
        ('view', 'Visualização'),
        ('click', 'Clique'),
        ('purchase', 'Compra'),
        ('rating', 'Avaliação'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Produto")
    interaction_type = models.CharField(
        max_length=20, 
        choices=INTERACTION_TYPES, 
        verbose_name="Tipo de Interação"
    )
    rating = models.IntegerField(null=True, blank=True, verbose_name="Avaliação (1-5)")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")
    
    class Meta:
        verbose_name = "Interação do Usuário"
        verbose_name_plural = "Interações dos Usuários"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.interaction_type}"

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    recommended_products = models.ManyToManyField(Product, verbose_name="Produtos Recomendados")
    model_version = models.CharField(max_length=50, default="v1.0", verbose_name="Versão do Modelo")
    confidence_score = models.FloatField(default=0.0, verbose_name="Pontuação de Confiança")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Recomendação"
        verbose_name_plural = "Recomendações"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recomendações para {self.user.username}"