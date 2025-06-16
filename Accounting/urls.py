from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from Accounting import views

urlpatterns = [
    # Gestione GAE
    path('gae/', views.GAElist.as_view(), name='acc_gae_list'),
    path('gae/add', views.GAEadd.as_view(), name='acc_gae_add'),
    path('gae/<int:pk>/mod', views.GAEmod.as_view(), name='acc_gae_mod'),
    path('gae/<int:pk>/del', views.GAEdel.as_view(), name='acc_gae_del'),
    path('residui', views.GAEResidui.as_view(), name='acc_gae_residui'),
    path('situazione', views.GAESituazione.as_view(), name='acc_gae_situazione'),
    path('impegni', views.GAEImpegni.as_view(), name='acc_gae_impegni'),
    #path('impegni/raw/<int:gae>', views.GAEImpegniRaw.as_view(), name='acc_gae_impegni_raw'),

    # Splitted accounting
    path('split', views.SplitAccounting.as_view(), name='acc_split_contab'),
    path('split/add', views.SplitAccountingAdd.as_view(), name='acc_split_contab_add'),
    path('split/<int:pk>', views.SplitAccountingDetail.as_view(), name='acc_split_contab_detail'),
    path('split/<int:pk>/mod', views.SplitAccountingUpdate.as_view(), name='acc_split_contab_mod'),
    path('split/<int:pk>/del', views.SplitAccountingDelete.as_view(), name='acc_split_contab_del'),
    path('split/<int:pk>/budget', views.SplitAccountingBudgetList.as_view(), name='acc_split_budget_list'),
    path('split/<int:pk>/budget/add', views.SplitAccountingBudgetAdd.as_view(), name='acc_split_budget_add'),
    path('split/<int:pk>/budget/<int:bpk>/mod', views.SplitAccountingBudgetUpdate.as_view(), name='acc_split_budget_mod'),
    path('split/<int:pk>/budget/<int:bpk>/del', views.SplitAccountingBudgetDelete.as_view(), name='acc_split_budget_del'),
    path('split/<int:pk>/del', views.SplitAccountingDelete.as_view(), name='acc_split_contab_del'),
    path('split/<int:pk>/impegni/add', views.SplitImpegniAdd.as_view(), name='acc_split_impegni_add'),
    path('split/<int:pk>/impegni/del', views.SplitImpegniDelete.as_view(), name='acc_split_impegni_del'),
    path('split/variazioni/add/<int:gae>', views.SplitVariazioniAdd.as_view(), name='acc_split_var_add'),
    path('split/variazioni/<int:vpk>/mod', views.SplitVariazioniUpdate.as_view(), name='acc_split_var_mod'),
    path('split/variazioni/<int:vpk>/del', views.SplitVariazioniDelete.as_view(), name='acc_split_var_del'),

    # Founding
    path('funding', views.Funding.as_view(), name='acc_funding'),

    # Ajax
    path('ajax/<int:gae>/situazione', views.GAEAjaxSituazione.as_view(), name='acc_ajax_gae_situazione'),
    path('ajax/<int:gae>/impegni', views.GAEAjaxImpegni.as_view(), name='acc_ajax_gae_impegni'),
    path('ajax/impegni/<int:impegno>/mandati', views.GAEAjaxMandati.as_view(), name='acc_ajax_mandati'),
    path('ajax/mandati/<int:mandato>', views.GAEAjaxDettagliMandato.as_view(), name='acc_ajax_mandato_details'),
    path('ajax/split/summary', views.SplitAccountingSummaryAjax.as_view(), name='acc_ajax_split_summary'),
    path('ajax/split/<int:pk>/impegni/add', views.SplitImpegniAjax.as_view(), name="acc_ajax_split_impegni"),
]

menu = {
    'name': 'Accounting',
    'link': '',
    'icon': 'fa-solid fa-sack-dollar',
    'subsections': [
        {
            'name': 'GAE',
            'link': reverse_lazy('acc_gae_list'),
            'permissions': ['Accounting.gae_manage', 'Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': "Up to date 'residui'",
            'link': reverse_lazy('acc_gae_residui'),
            'permissions': ['Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': "'Situazione' GAE",
            'link': reverse_lazy('acc_gae_situazione'),
            'permissions': ['Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': "'Impegni' GAE",
            'link': reverse_lazy('acc_gae_impegni'),
            'permissions': ['Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': "Split accounting",
            'link': reverse_lazy('acc_split_contab'),
            'permissions': ['Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': "Funding",
            'link': reverse_lazy('acc_funding'),
            'permissions': ['Accounting.gae_view', 'Accounting.gae_view_own'],
        },
        {
            'name': 'SIGLA manual',
            'link': reverse_lazy('sigla_manual_main'),
            'permissions': ['Accounting.gae_manage'],
        },
    ],
    'permissions': ['Accounting.gae_manage', 'Accounting.gae_view', 'Accounting.gae_view_own'],
}
