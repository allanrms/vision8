from django import forms
from agents.models import LLMProviderConfig, AssistantContextFile
from .file_processors import file_processor


class AssistantForm(forms.ModelForm):
    """
    Formulário para criar e editar assistants (LLMProviderConfig)
    """
    
    class Meta:
        model = LLMProviderConfig
        fields = ['display_name', 'name', 'model', 'instructions', 'temperature', 'max_tokens', 
                  'top_p', 'presence_penalty', 'frequency_penalty']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Assistant de Vendas, Suporte Técnico, Especialista em Ciclismo'
            }),
            'name': forms.Select(attrs={
                'class': 'form-select'
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: gpt-4o-mini, gpt-3.5-turbo, gpt-4, claude-3-sonnet'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'Exemplo:\n\nVocê é um assistente especializado em vendas de bicicletas.\n\nComportamento:\n- Seja amigável e entusiasmado sobre ciclismo\n- Sempre pergunte sobre o uso pretendido antes de recomendar\n- Ofereça opções dentro do orçamento do cliente\n\nRegras:\n- Nunca recomende produtos que não temos em estoque\n- Sempre mencione a garantia e manutenção\n- Se não souber algo, encaminhe para um especialista'
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'max': '2'
            }),
            'max_tokens': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '4000'
            }),
            'top_p': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            }),
            'presence_penalty': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '-2',
                'max': '2'
            }),
            'frequency_penalty': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '-2',
                'max': '2'
            })
        }
        labels = {
            'display_name': 'Nome do Assistant',
            'name': 'Provedor de IA',
            'model': 'Modelo',
            'instructions': 'Instruções do Assistant',
            'temperature': 'Temperatura',
            'max_tokens': 'Máximo de Tokens',
            'top_p': 'Top-p',
            'presence_penalty': 'Penalidade de Presença',
            'frequency_penalty': 'Penalidade de Frequência'
        }
        help_texts = {
            'display_name': 'Nome personalizado para identificar este assistant (ex: "Suporte Técnico", "Vendedor Expert")',
            'name': 'Escolha o provedor de IA (OpenAI, Anthropic, etc)',
            'model': 'Nome específico do modelo (ex: gpt-4o-mini, gpt-3.5-turbo)',
            'instructions': 'Defina a personalidade, comportamento e regras do seu assistant. Use frases claras e específicas.',
            'temperature': 'Controla criatividade (0.0 = conservador, 2.0 = criativo)',
            'max_tokens': 'Limite máximo de tokens na resposta',
            'top_p': 'Amostragem nuclear - controla diversidade da resposta',
            'presence_penalty': 'Penaliza repetição de tópicos (-2.0 a 2.0)',
            'frequency_penalty': 'Penaliza repetição de palavras (-2.0 a 2.0)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marca campos obrigatórios
        self.fields['display_name'].required = True
        self.fields['name'].required = True
        self.fields['model'].required = True
        self.fields['instructions'].required = True
        
        # Os valores padrão são definidos na view AssistantCreateView.get_initial()
        # Não precisamos definir aqui para evitar conflitos
    
    def clean_display_name(self):
        """
        Valida o nome de exibição
        """
        display_name = self.cleaned_data.get('display_name')
        
        if not display_name:
            raise forms.ValidationError('Nome do Assistant é obrigatório')
        
        # Remove espaços
        display_name = display_name.strip()
        
        if len(display_name) < 3:
            raise forms.ValidationError('Nome do Assistant deve ter pelo menos 3 caracteres')
        
        return display_name
    
    def clean_model(self):
        """
        Valida o nome do modelo
        """
        model = self.cleaned_data.get('model')
        
        if not model:
            raise forms.ValidationError('Nome do modelo é obrigatório')
        
        # Remove espaços
        model = model.strip()
        
        if len(model) < 3:
            raise forms.ValidationError('Nome do modelo deve ter pelo menos 3 caracteres')
        
        return model
    
    def clean_instructions(self):
        """
        Valida as instruções
        """
        instructions = self.cleaned_data.get('instructions')
        
        if not instructions:
            raise forms.ValidationError('Instruções são obrigatórias')
        
        instructions = instructions.strip()
        
        if len(instructions) < 10:
            raise forms.ValidationError('Instruções devem ter pelo menos 10 caracteres')
        
        return instructions


class AssistantSearchForm(forms.Form):
    """
    Formulário de busca para assistants
    """
    search = forms.CharField(
        label='Buscar',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome, modelo ou instruções...',
            'autocomplete': 'off'
        })
    )
    
    provider = forms.ChoiceField(
        label='Provedor',
        choices=[('', 'Todos os provedores')] + list(LLMProviderConfig.PROVIDERS),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class AssistantContextFileForm(forms.ModelForm):
    """
    Formulário para upload de arquivos de contexto
    """
    
    class Meta:
        model = AssistantContextFile
        fields = ['name', 'file', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Manual do produto, FAQ, Políticas da empresa'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.txt,.docx,.md,.csv,.json,.html'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        
        labels = {
            'name': 'Nome do arquivo',
            'file': 'Arquivo',
            'is_active': 'Ativo'
        }
        
        help_texts = {
            'name': 'Nome descritivo para identificar o arquivo',
            'file': 'Formatos suportados: PDF, TXT, DOCX, MD, CSV, JSON, HTML (máx. 10MB)',
            'is_active': 'Se desativado, o arquivo não será usado como contexto'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Marcar campos obrigatórios
        self.fields['name'].required = True
        self.fields['file'].required = True
        
    def clean_file(self):
        """
        Valida o arquivo enviado
        """
        uploaded_file = self.cleaned_data.get('file')
        
        if not uploaded_file:
            return uploaded_file
            
        # Verificar tamanho (10MB)
        max_size = 10 * 1024 * 1024
        if uploaded_file.size > max_size:
            raise forms.ValidationError(f'Arquivo muito grande. Máximo permitido: {max_size / (1024*1024):.1f}MB')
        
        # Verificar extensão
        file_name = uploaded_file.name.lower()
        supported_extensions = file_processor.get_supported_extensions()
        
        file_extension = None
        for ext in supported_extensions:
            if file_name.endswith(ext):
                file_extension = ext
                break
                
        if not file_extension:
            supported_list = ', '.join(supported_extensions)
            raise forms.ValidationError(f'Tipo de arquivo não suportado. Formatos aceitos: {supported_list}')
        
        return uploaded_file
    
    def clean_name(self):
        """
        Valida o nome do arquivo
        """
        name = self.cleaned_data.get('name')
        
        if not name:
            raise forms.ValidationError('Nome é obrigatório')
        
        # Remove espaços
        name = name.strip()
        
        if len(name) < 3:
            raise forms.ValidationError('Nome deve ter pelo menos 3 caracteres')
        
        return name