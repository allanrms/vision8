from django.contrib import admin
from django.utils.html import format_html
from .models import EvolutionInstance, MessageHistory, ImageProcessingJob, ChatSession


@admin.register(EvolutionInstance)
class EvolutionInstanceAdmin(admin.ModelAdmin):
    """
    Admin para gerenciar instâncias Evolution API
    """
    list_display = ['name', 'instance_name', 'owner', 'status_badge', 'connection_info',
                    'llm_config_display', 'is_active', 'created_at', 'last_connection']
    list_filter = ['status', 'is_active', 'owner', 'llm_config', 'created_at']
    search_fields = ['name', 'instance_name', 'phone_number', 'profile_name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at', 'last_connection']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'instance_name', 'owner', 'is_active')
        }),
        ('Configuração Evolution API', {
            'fields': ('webhook_url',)
        }),
        ('Configuração de IA', {
            'fields': ('llm_config',)
        }),
        ('Status da Conexão', {
            'fields': ('status', 'phone_number', 'profile_name', 'profile_pic_url')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at', 'last_connection')
        }),
    )
    
    def status_badge(self, obj):
        """Exibe status com badge colorido"""
        colors = {
            'connected': 'success',
            'connecting': 'warning', 
            'disconnected': 'secondary',
            'error': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def connection_info(self, obj):
        """Exibe informações de conexão formatadas"""
        return obj.connection_info
    connection_info.short_description = 'Conexão'
    
    def llm_config_display(self, obj):
        """Exibe configuração LLM formatada"""
        if obj.llm_config:
            return format_html(
                '<span class="badge bg-info">{}</span>',
                str(obj.llm_config)
            )
        return format_html('<span class="text-muted">Não configurado</span>')
    llm_config_display.short_description = 'Configuração LLM'
    
    def save_model(self, request, obj, form, change):
        """Define o usuário atual como owner se não foi especificado"""
        if not change:  # Criação de nova instância
            if not obj.owner:
                obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """
    Admin para gerenciar sessões de chat
    """
    list_display = ('id', 'from_number', 'to_number', 'owner', 'status', 'message_count', 'created_at', 'updated_at')
    list_filter = ('status', 'owner', 'evolution_instance', 'created_at', 'updated_at')
    search_fields = ('from_number', 'to_number', 'owner__username', 'owner__first_name', 'owner__email')
    readonly_fields = ('created_at', 'updated_at', 'message_count')
    list_editable = ('status', )
    autocomplete_fields = ['owner']

    fieldsets = (
        ('Session Info', {
            'fields': ('from_number', 'to_number', 'owner', 'status', 'evolution_instance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
        ('Statistics', {
            'fields': ('message_count',)
        }),
    )
    
    def get_owner(self, obj):
        """Retorna o usuário dono da sessão"""
        if obj.owner:
            return format_html(
                '<span title="{}">{}</span>',
                obj.owner.email,
                obj.owner.username
            )
        return '-'
    get_owner.short_description = 'Usuário'
    get_owner.admin_order_field = 'owner__username'

    def status_badge(self, obj):
        """Exibe status com badge colorido"""
        colors = {
            'ai': 'primary',
            'human': 'success',
            'closed': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def message_count(self, obj):
        """Retorna o número de mensagens na sessão"""
        return obj.messages.count()
    message_count.short_description = 'Mensagens'


@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ('chat_session_id', 'get_from_number', 'get_owner', 'sender_name', 'message_type', 'content_preview', 'processing_status', 'inactive_badge', 'created_at', 'received_at')
    list_filter = ('message_type', 'processing_status', 'received_while_inactive', 'owner', 'received_at', 'created_at')
    search_fields = ('message_id', 'chat_session__from_number', 'content', 'sender_name', 'owner__username', 'owner__first_name')
    readonly_fields = ('message_id', 'created_at', 'received_at', 'updated_at')

    fieldsets = (
        ('Message Info', {
            'fields': ('message_id', 'chat_session', 'owner', 'message_type', 'created_at', 'received_at', 'updated_at')
        }),
        ('Content', {
            'fields': ('content', 'media_url', 'media_file')
        }),
        ('Sender Info', {
            'fields': ('sender_name', 'source')
        }),
        ('Processing', {
            'fields': ('processing_status', 'response', 'audio_transcription', 'received_while_inactive')
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
    )
    
    def get_from_number(self, obj):
        """Retorna o número de origem da sessão de chat"""
        return obj.chat_session.from_number if obj.chat_session else '-'
    get_from_number.short_description = 'From Number'
    get_from_number.admin_order_field = 'chat_session__from_number'

    def get_owner(self, obj):
        """Retorna o usuário dono da mensagem"""
        if obj.owner:
            return format_html(
                '<span title="{}">{}</span>',
                obj.owner.email,
                obj.owner.username
            )
        return '-'
    get_owner.short_description = 'Usuário'
    get_owner.admin_order_field = 'owner__username'

    def content_preview(self, obj):
        """Exibe preview do conteúdo (limitado a 50 caracteres)"""
        if obj.content:
            content = obj.content[:50]
            if len(obj.content) > 50:
                content += '...'
            return content
        return '-'
    content_preview.short_description = 'Conteúdo'

    def inactive_badge(self, obj):
        """Exibe badge se mensagem foi recebida com instância inativa"""
        if obj.received_while_inactive:
            return format_html('<span class="badge bg-warning" title="Recebida com instância inativa">🔴 Inativa</span>')
        return format_html('<span class="badge bg-success" title="Recebida com instância ativa">✅ Ativa</span>')
    inactive_badge.short_description = 'Status da Instância'
    inactive_badge.admin_order_field = 'received_while_inactive'


@admin.register(ImageProcessingJob)
class ImageProcessingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'processor_type', 'status', 'created_at', 'completed_at')
    list_filter = ('processor_type', 'status', 'created_at')
    search_fields = ('message__message_id', 'message__chat_session__from_number')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    
    fieldsets = (
        ('Job Info', {
            'fields': ('message', 'processor_type', 'status')
        }),
        ('Timing', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('result', 'error_message'),
            'classes': ('collapse',)
        }),
    )