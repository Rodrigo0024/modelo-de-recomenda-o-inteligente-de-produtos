import os
import requests
import json
import random
from django.conf import settings

class AIGenerator:
    """
    Serviço de IA Generativa usando DeepSeek API
    Versão melhorada para descrições únicas e criativas
    """
    
    def __init__(self):
        # Configurações do .env
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
        self.api_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.model = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')
        self.max_tokens = getattr(settings, 'AI_MAX_TOKENS', 1000)
        self.temperature = getattr(settings, 'AI_TEMPERATURE', 0.8)
        
        print(f"🤖 IA Generativa Configurada:")
        print(f"   Provider: {getattr(settings, 'AI_PROVIDER', 'deepseek')}")
        print(f"   API Key: {'✅ Configurada' if self._is_configured() else '❌ Não configurada'}")
        print(f"   Model: {self.model}")
    
    def generate_product_description(self, product_name, category, price, features=None):
        """
        Gera uma descrição única e personalizada para cada produto
        """
        try:
            # ✅ Seleciona um estilo criativo aleatório para variar
            writing_style = self._get_random_writing_style()
            tone = self._get_random_tone()
            focus_angle = self._get_random_focus_angle()
            
            prompt = self._build_creative_prompt(
                product_name, category, price, features, 
                writing_style, tone, focus_angle
            )
            
            # Verificar se a API key está configurada
            if not self._is_configured():
                print("⚠️ API Key não configurada - usando fallback criativo")
                return self._creative_fallback_description(product_name, category, price, features)
            
            # Chamada para DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            return response.strip()
            
        except Exception as e:
            print(f"❌ Erro na geração de descrição: {e}")
            return self._creative_fallback_description(product_name, category, price, features)
    
    def _is_configured(self):
        """Verifica se a API está configurada corretamente"""
        return bool(self.api_key and self.api_key != 'sua-chave-real-da-deepseek-aqui')
    
    def _get_random_writing_style(self):
        """Retorna um estilo de escrita aleatório para variar as descrições"""
        styles = [
            "storytelling",           # Conta uma história
            "problem_solution",       # Problema + Solução
            "benefit_focused",        # Foco nos benefícios
            "comparative",           # Compara com alternativas
            "testimonial_style",     # Estilo depoimento
            "question_based",        # Baseado em perguntas
            "feature_highlight",     # Destaque de features
            "lifestyle_focused",     # Foco no estilo de vida
            "technical_expert",      # Especialista técnico
            "emotional_appeal"       # Apelo emocional
        ]
        return random.choice(styles)
    
    def _get_random_tone(self):
        """Retorna um tom de voz aleatório"""
        tones = [
            "entusiasmado e energético",
            "conversacional e amigável", 
            "sofisticado e premium",
            "prático e direto",
            "inspirador e motivacional",
            "humorístico e descontraído",
            "autoritário e especialista",
            "cuidadoso e detalhista",
            "urgente e exclusivo",
            "calmo e confiante"
        ]
        return random.choice(tones)
    
    def _get_random_focus_angle(self):
        """Retorna um ângulo de foco diferente para cada produto"""
        angles = [
            "inovação e tecnologia",
            "conveniência no dia a dia",
            "economia e custo-benefício",
            "qualidade e durabilidade",
            "design e estética",
            "sustentabilidade e eco-friendly",
            "status e exclusividade", 
            "segurança e confiabilidade",
            "personalização e adaptação",
            "experiência do usuário"
        ]
        return random.choice(angles)
    
    def _build_creative_prompt(self, product_name, category, price, features, style, tone, focus_angle):
        """
        Constrói prompts criativos e únicos para cada produto
        """
        features_text = ""
        if features:
            features_text = f"\nCaracterísticas principais: {features}"
        
        style_prompts = {
            "storytelling": f"""
            Conte uma pequena história sobre como o {product_name} transforma o dia a dia das pessoas.
            Comece com uma situação comum que o produto resolve de forma extraordinária.
            """,
            
            "problem_solution": f"""
            Identifique um problema comum que as pessoas enfrentam e mostre como o {product_name} 
            é a solução perfeita. Use o formato: "Problema → Solução → Resultado".
            """,
            
            "benefit_focused": f"""
            Foque nos BENEFÍCIOS reais que o {product_name} oferece, não apenas nas características.
            Responda à pergunta: "O que este produto realmente faz pela vida do cliente?"
            """,
            
            "comparative": f"""
            Compare sutilmente o {product_name} com alternativas do mercado, destacando suas 
            vantagens únicas sem mencionar marcas concorrentes diretamente.
            """,
            
            "testimonial_style": f"""
            Escreva como se fosse um depoimento genuíno de um cliente satisfeito que descobriu 
            o {product_name} e teve sua experiência transformada.
            """,
            
            "question_based": f"""
            Comece com uma pergunta provocativa que o cliente potencial estaria se fazendo.
            Então responda mostrando como o {product_name} é a resposta que ele procura.
            """,
            
            "feature_highlight": f"""
            Destaque as características mais impressionantes do {product_name} de forma que 
            o cliente entenda imediatamente o valor de cada uma.
            """,
            
            "lifestyle_focused": f"""
            Descreva como o {product_name} se encaixa perfeitamente em um estilo de vida 
            desejável e quais experiências ele possibilita.
            """,
            
            "technical_expert": f"""
            Use uma linguagem que demonstre expertise técnica sobre {category}, mas de forma 
            acessível que qualquer pessoa entenda os diferenciais do {product_name}.
            """,
            
            "emotional_appeal": f"""
            Conecte-se emocionalmente com o cliente, mostrando como o {product_name} não é 
            apenas um produto, mas uma experiência que traz felicidade, segurança ou realização.
            """
        }
        
        base_prompt = f"""
        VOCÊ É: Um copywriter criativo especializado em e-commerce, com talento para criar descrições únicas e memoráveis.

        PRODUTO:
        - Nome: {product_name}
        - Categoria: {category}
        - Preço: R$ {price}
        {features_text}

        ABORDAGEM CRIATIVA:
        - Estilo: {style_prompts[style]}
        - Tom de Voz: {tone}
        - Ângulo Principal: {focus_angle}

        FORMATO E ESTILO:
        - Idioma: Português brasileiro natural
        - Comprimento: 120-180 palavras
        - Estrutura: Livre e criativa (não use bullet points padronizados)
        - Use emojis de forma estratégica e moderada
        - Seja autêntico e evite clichês de marketing

        REGRAS IMPORTANTES:
        - NÃO use "🌟 **Nome do Produto**" no início
        - NÃO use estruturas padronizadas com 💫, 🎯, 🚀
        - Crie uma introdução cativante e única
        - Finalize com uma chamada para ação natural
        - Cada descrição deve ser completamente diferente das outras

        Gere APENAS a descrição final, sem comentários ou marcações.
        """
        
        return base_prompt
    
    def _call_deepseek_api(self, prompt):
        """
        Faz a chamada para a DeepSeek API
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'system', 
                        'content': 'Você é um copywriter criativo e inovador. Sua especialidade é criar descrições únicas e memoráveis para produtos, sempre variando o estilo e abordagem.'
                    },
                    {
                        'role': 'user', 
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': 0.9,  # ✅ Temperatura mais alta para mais criatividade
                'top_p': 0.95,       # ✅ Mais variação nas respostas
                'stream': False
            }
            
            print(f"🔗 Chamando DeepSeek API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"✅ Descrição única gerada com sucesso!")
                return content
            else:
                error_msg = f"DeepSeek API Error: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            print("⏰ Timeout na chamada da API")
            return self._creative_fallback_description_from_prompt(prompt)
        except Exception as e:
            print(f"❌ Erro na API DeepSeek: {e}")
            return self._creative_fallback_description_from_prompt(prompt)
    
    def _creative_fallback_description(self, product_name, category, price, features=None):
        """Fallback criativo quando a API não está disponível"""
        fallback_styles = [
            # Estilo storytelling
            f"""Imagine chegar em casa após um longo dia e encontrar a solução que simplifica sua rotina: o {product_name}. 
            
Desenvolvido especialmente para quem busca praticidade sem abrir mão da qualidade, este produto da categoria {category} chega para transformar sua experiência. Com investimento de R$ {price}, você adquire não apenas um item, mas um aliado no seu dia a dia.

{features if features else "Cada detalhe foi pensado para oferecer o máximo de valor."}

Descubra por que tantas pessoas já escolheram o {product_name} e nunca mais voltaram atrás. 🏆""",

            # Estilo benefício-focado
            f"""O que você realmente ganha ao escolher o {product_name}? 

Mais tempo livre, menos preocupações e resultados que superam expectativas. Por apenas R$ {price}, esta aquisição na categoria {category} entrega performance excepcional com o equilíbrio perfeito entre custo e benefício.

{features + " " if features else ""}São diferenciais que fazem toda a diferença quando o assunto é satisfação garantida.

Não espere para transformar sua experiência - o momento ideal é agora! ✨""",

            # Estilo técnico
            f"""ANÁLISE DO {product_name.upper()}:

Especialistas em {category} concordam: este produto estabelece novos padrões em sua categoria. Com valor acessível de R$ {price}, o {product_name} entrega especificações impressionantes:

{features if features else "Performance otimizada e construção durável"}

Resultado: eficiência comprovada e durabilidade excepcional. 

Para quem busca excelência técnica sem complicações. 🔧"""
        ]
        
        return random.choice(fallback_styles)
    
    def _creative_fallback_description_from_prompt(self, prompt):
        """Fallback criativo baseado no prompt quando a API falha"""
        try:
            # Tenta extrair informações do prompt para personalizar o fallback
            product_name = self._extract_product_name(prompt)
            category = self._extract_category(prompt)
            
            creative_lines = [
                f"Descubra o {product_name} - uma revolução em {category} que redefine expectativas.",
                f"O {product_name} chegou para transformar completamente sua experiência com {category}.",
                f"Imagine um {product_name} que entrega tudo o que você precisa e um pouco mais...",
                f"Prepare-se para se surpreender com o {product_name}: onde inovação encontra praticidade.",
                f"O segredo para uma experiência excepcional em {category}? Conheça o {product_name}."
            ]
            
            return random.choice(creative_lines)
        except:
            return "Produto de altíssima qualidade com desempenho excepcional. Experiência garantida! 🚀"
    
    def _extract_product_name(self, prompt):
        """Extrai o nome do produto do prompt"""
        try:
            lines = prompt.split('\n')
            for line in lines:
                if 'Nome:' in line:
                    return line.split('Nome:')[-1].strip()
        except:
            pass
        return "este produto"
    
    def _extract_category(self, prompt):
        """Extrai a categoria do produto do prompt"""
        try:
            lines = prompt.split('\n')
            for line in lines:
                if 'Categoria:' in line:
                    return line.split('Categoria:')[-1].strip()
        except:
            pass
        return "sua categoria"
    
    def generate_product_features(self, product_name, category):
        """
        Gera features únicas e criativas para cada produto
        """
        style = random.choice(["technical", "benefits", "lifestyle", "comparative"])
        
        style_prompts = {
            "technical": f"Liste 5-7 especificações técnicas únicas do {product_name} em {category}",
            "benefits": f"Converta as características do {product_name} em 5-7 benefícios tangíveis para o usuário",
            "lifestyle": f"Descreva 5-7 formas como o {product_name} melhora o estilo de vida ou rotina",
            "comparative": f"Destaque 5-7 vantagens competitivas únicas do {product_name} em {category}"
        }
        
        prompt = f"""
        {style_prompts[style]}
        
        Formato: lista curta separada por vírgulas
        Idioma: Português brasileiro
        Seja específico e evite generalizações
        """
        
        try:
            if self._is_configured():
                response = self._call_deepseek_api(prompt)
                features = response.strip().replace('\n', ', ').replace('"', '')
                # Garante que não tenha mais que 7 features
                features_list = [f.strip() for f in features.split(',')]
                return ', '.join(features_list[:7])
            else:
                return self._fallback_features(category)
        except Exception as e:
            print(f"❌ Erro ao gerar features: {e}")
            return self._fallback_features(category)
    
    def _fallback_features(self, category):
        """Features fallback variadas"""
        fallback_features = {
            'eletrônicos': ['Performance otimizada', 'Design ergonômico', 'Bateria de longa duração', 'Conectividade avançada', 'Atualizações garantidas'],
            'livros': ['Edição especial', 'Conteúdo exclusivo', 'Ilustrações premium', 'Papel de alta qualidade', 'Encadernação durável'],
            'roupas': ['Tecido tecnológico', 'Corte moderno', 'Conforto garantido', 'Durabilidade comprovada', 'Estilo versátil'],
            'casa': ['Design inteligente', 'Fácil manutenção', 'Material premium', 'Funcionalidade comprovada', 'Estilo atemporal'],
            'default': ['Qualidade superior', 'Design exclusivo', 'Performance comprovada', 'Durabilidade garantida', 'Valor excepcional']
        }
        
        features = fallback_features.get(category.lower(), fallback_features['default'])
        random.shuffle(features)  # Embaralha para variar
        return ', '.join(features[:5])