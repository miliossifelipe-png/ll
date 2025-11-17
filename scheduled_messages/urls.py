from django.urls import path
from . import views
from .views import (
    MessageBlocksPrototypeView,
    ScheduledMessageListView,
    ScheduledMessageCreateView,
    ScheduledMessageEditView,
    ScheduledMessageDeleteView,
)

urlpatterns = [
    path('', ScheduledMessageListView.as_view(), name='scheduled_message_list'),
    path('nova/', ScheduledMessageCreateView.as_view(), name='scheduled_message_create'),
    path('<int:pk>/editar/', ScheduledMessageEditView.as_view(), name='scheduled_message_edit'),
    path('<int:pk>/deletar/', ScheduledMessageDeleteView.as_view(), name='scheduled_message_delete'),
    path('blocos/prototipo/', MessageBlocksPrototypeView.as_view(), name='blocks_prototype'),
    path('ajax/upload-block-file/', views.ajax_upload_block_file, name='ajax_upload_block_file'),
    path('<int:pk>/testar/', views.testar_envio_mensagem, name='scheduled_message_testar'),
    path('deletar-em-lote/', views.ScheduledMessageBulkDeleteView.as_view(), name='scheduled_message_bulk_delete'),
    path('api/draft/', views.api_draftmessage, name='api_draftmessage'),
    path('rascunho/<uuid:uuid>/excluir/', views.DraftMessageDeleteView.as_view(), name='excluir_rascunho'),
    path('api/excluir-arquivo-bloco/', views.excluir_arquivo_bloco, name='excluir_arquivo_bloco'),
    path('rascunhos/deletar-em-lote/', views.DraftMessageBulkDeleteView.as_view(), name='draftmessage_bulk_delete'),
    path('api/remover-bloco/', views.remover_bloco, name='remover_bloco'),
    path('nova-draft/', views.novo_draft, name='novo_draft'),
] 