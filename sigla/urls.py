from django.urls import path, reverse_lazy

from sigla import views


urlpatterns = [
    path('manual/', views.SiglaManualView.as_view(), name='sigla_manual_main'),
    path('ajax/docs/', views.SiglaAjaxManualView.as_view(), name='sigla_manual_detail'),
    path('ajax/progetti/', views.SiglaProgetti.as_view(), name='sigla_progetti'),
    path('ajax/progetti/<int:pg_progetto>/gae', views.SiglaGAE.as_view(), name='sigla_gae'),
    path('ajax/gae/<str:gae>/competenza', views.SiglaGAECompetenza.as_view(), name='sigla_gae_competenza'),
    path('ajax/gae/<str:gae>/competenza/<int:esercizio>', views.SiglaGAECompetenza.as_view(), name='sigla_gae_competenza_esercizio'),
    path('ajax/gae/<str:gae>/residui', views.SiglaGAEResidui.as_view(), name='sigla_gae_residui'),
    path('ajax/gae/<str:gae>/impegni', views.SiglaGAEImpegni.as_view(), name='sigla_gae_impegni'),
    path('ajax/gae/<str:gae>/impegni/<int:esercizio>', views.SiglaGAEImpegni.as_view(), name='sigla_gae_impegni_esercizio'),
    path('ajax/gae/<str:gae>/variazioni', views.SiglaGAEVariazioni.as_view(), name='sigla_gae_variazioni'),
    path('ajax/gae/<str:gae>/variazioni/<int:esercizio>', views.SiglaGAEVariazioni.as_view(), name='sigla_gae_variazioni_esercizio'),
    path('ajax/mandati/<int:es_orig>/<int:pg_obb>', views.SiglaMandati.as_view(), name='sigla_mandati'),
    path('ajax/mandati/<int:es_orig>/<int:pg_obb>/<int:esercizio>', views.SiglaMandati.as_view(), name='sigla_mandati_esercizio'),
    # path('ajax/fatture/<int:pg_docamm>', views.SiglaFatture.as_view(), name='sigla_fatture'),
    path('ajax/fatture/<int:esercizio>/<int:pg_mandato>', views.SiglaFatture.as_view(), name='sigla_fatture'),
]