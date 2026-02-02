from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    # Dashboard
    path('', views.cms_dashboard, name='dashboard'),
    
    # Pages
    path('pages/', views.pages_list, name='pages_list'),
    path('pages/new/', views.page_editor, name='page_new'),
    path('pages/<uuid:page_id>/edit/', views.page_editor, name='page_edit'),
    path('pages/<uuid:page_id>/duplicate/', views.duplicate_page, name='page_duplicate'),
    path('pages/<uuid:page_id>/delete/', views.delete_page, name='page_delete'),
    path('pages/<uuid:page_id>/revert/<int:version_number>/', views.revert_page_version, name='page_revert'),
    
    # API endpoints
    path('api/pages/save/', views.save_page, name='save_page'),
    path('api/pages/<uuid:page_id>/data/', views.get_page_data, name='get_page_data'),
    
    # Blocks
    path('blocks/', views.blocks_library, name='blocks_library'),
    path('api/blocks/create/', views.create_block, name='create_block'),
    path('api/blocks/<uuid:block_id>/data/', views.get_block_data, name='get_block_data'),
    
    # Media
    path('media/', views.media_library, name='media_library'),
    path('api/media/upload/', views.upload_media, name='upload_media'),
]
