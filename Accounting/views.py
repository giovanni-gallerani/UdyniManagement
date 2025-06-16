import datetime
import re
from collections import OrderedDict

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F, Sum, Value, ExpressionWrapper, IntegerField, CharField
from django.db.models.functions import Coalesce
from django.views import View

from UdyniManagement.menu import UdyniMenu
from UdyniManagement.views import ListViewMenu, CreateViewMenu, TemplateViewMenu, UpdateViewMenu, DeleteViewMenu

from Accounting.models import VoceSpesa, GAE, Stanziamento, Variazione, Impegno, Mandato
from Accounting.models import SplitContab, SplitBudget, SplitImpegno, SplitVariazione
from Accounting.forms import GaeForm
from Accounting.utils import create_split_accounting_detail


# =============================
# Gestione GAE

class GAElist(PermissionRequiredMixin, ListViewMenu):
    model = GAE
    permission_required = 'Accounting.gae_view'
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get_queryset(self):
        if self.only_own_gae:
            return GAE.objects.filter(Q(project__pi__username=self.request.user)).order_by('name')
        else:
            return GAE.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "GAE"
        context['can_edit'] = self.request.user.has_perm('Accounting.gae_manage')
        return context


class GAEadd(PermissionRequiredMixin, CreateViewMenu):
    model = GAE
    form_class = GaeForm
    template_name = "Accounting/gae_form.html"
    permission_required = "Accounting.gae_manage"

    def get_success_url(self):
        return reverse_lazy('acc_gae_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new GAE"
        context['back_url'] = self.get_success_url()
        return context


class GAEmod(PermissionRequiredMixin, UpdateViewMenu):
    model = GAE
    fields = ['description', 'include_funding']
    template_name = "Accounting/gae_form.html"
    permission_required = "Accounting.gae_manage"

    def get_success_url(self):
        return reverse_lazy('acc_gae_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify GAE"
        context['back_url'] = self.get_success_url()
        return context


class GAEdel(PermissionRequiredMixin, DeleteViewMenu):
    model = GAE
    template_name = "UdyniManagement/confirm_delete.html"
    permission_required = "Accounting.gae_manage"

    def get_success_url(self):
        return reverse_lazy('acc_gae_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete GAE"
        context['message'] = "Are you sure you want to delete the GAE: {0!s}?".format(
            context['object'])
        context['back_url'] = self.get_success_url()
        return context


# =============================
# Residui in tempo reale. Sintetici.

class GAEResidui(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        if self.only_own_gae:
            objects = GAE.objects.filter(Q(project__pi__username=request.user)).order_by('name')
        else:
            objects = GAE.objects.all().order_by('name')
        gae = []
        for obj in objects:
            gae.append({
                'name': obj.name,
                'desc': obj.description,
                'project': obj.project.name,
            })

        context = {
            'title': 'Available funds',
            'gae': gae,
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'Accounting/gae_residui.html', context)


# ===============================
# Situazione GAE dettagliata (stanziamenti, variazioni, spese)

class GAESituazione(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        if self.only_own_gae:
            objects = GAE.objects.filter(Q(project__pi__username=request.user)).order_by('name')
        else:
            objects = GAE.objects.all().order_by('name')
        gae = []
        for obj in objects:
            gae.append({
                'pk': obj.pk,
                'name': obj.name,
                'desc': obj.description,
                'project': obj.project.name,
            })

        context = {
            'title': "'Situazione' GAE",
            'gae': gae,
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'Accounting/gae_situazione.html', context)


class GAEAjaxSituazione(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        # Get GAE
        gae = get_object_or_404(GAE, pk=self.kwargs['gae'])
        if self.only_own_gae and gae.project.pi.username != request.user:
            self.handle_no_permission()

        situazione, totals = self.__build_situazione(gae)
        voci = {}
        for v in situazione.keys():
            voci[v] = VoceSpesa.objects.get(voce=v).description

        context = {
            'situazione': situazione,
            'totals': totals,
            'voci': voci,
        }
        # Return formatted table through AJAX
        return render(request, 'Accounting/gae_situazione_table.html', context)

    def __build_situazione(self, gae):

        stanziamenti = (
            Stanziamento.objects
            .filter(gae=gae)
            .order_by('voce', 'esercizio')
        )

        variazioni = (
            Variazione.objects
            .filter(gae=gae)
            .order_by('voce', 'esercizio', 'data')
        )

        situazione = {}

        for s in stanziamenti:

            voce = s.voce.voce
            if voce not in situazione:
                situazione[voce] = {}

            situazione[voce][s.esercizio] = {
                'stanziamento': s.stanziamento,
                'assestato': s.assestato,
                'var_piu': s.var_piu,
                'var_meno': s.var_meno,
                'impegnato': s.impegnato,
                'pagato': s.pagato,
                'residuo': s.residuo,
                'variazioni': [],
            }

        for v in variazioni:

            voce = v.voce.voce

            if voce not in situazione:
                print("[E] variazione su voce non presente nella situazione!")
                continue

            if v.esercizio not in situazione[voce]:
                print("[E] variazione su esercizio non presenze nella situazione!")
                continue

            situazione[voce][v.esercizio]['variazioni'].append({
                'numero': v.numero,
                'descrizione': v.descrizione,
                'importo': v.importo,
                'data': v.data,
            })

        # Totals
        totals = {
            'stanziamento': 0.0,
            'assestato': 0.0,
            'var_piu': 0.0,
            'var_meno': 0.0,
            'impegnato': 0.0,
            'pagato': 0.0,
            'residuo': 0.0,
        }
        for voce, esercizi in situazione.items():
            for esercizio, data in esercizi.items():
                totals['stanziamento'] += data['stanziamento']
                totals['assestato'] += data['assestato']
                totals['var_piu'] += data['var_piu']
                totals['var_meno'] += data['var_meno']
                totals['impegnato'] += data['impegnato']
                totals['pagato'] += data['pagato']
                totals['residuo'] += data['residuo']

        return situazione, totals


# =================================
# GAE dettaglio impegni
class GAEImpegni(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        if self.only_own_gae:
            objects = GAE.objects.filter(Q(project__pi__username=request.user)).order_by('name')
        else:
            objects = GAE.objects.all().order_by('name')
        gae = []
        for obj in objects:
            gae.append({
                'pk': obj.pk,
                'name': obj.name,
                'desc': obj.description,
                'project': obj.project.name,
            })

        context = {
            'title': "'Impegni' GAE",
            'gae': gae,
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'Accounting/gae_impegni.html', context)


class GAEImpegniRaw(PermissionRequiredMixin, ListViewMenu):
    model = Impegno
    template_name = "Accounting/gae_impegni_raw.html"
    permission_required = 'Accounting.gae_manage'

    def get_queryset(self):
        gae = get_object_or_404(GAE, pk=self.kwargs['gae'])
        return Impegno.objects.filter(gae=gae).order_by('esercizio_orig', 'numero', 'esercizio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gae = get_object_or_404(GAE, pk=self.kwargs['gae'])
        context['title'] = "Impegni for GAE {0:s}".format(gae.name)
        return context


class GAEAjaxImpegni(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):

        gae = get_object_or_404(GAE, pk=self.kwargs['gae'])

        if self.only_own_gae and gae.project.pi.username != request.user:
            self.handle_no_permission()

        m_prev = (
            Mandato.objects
            .filter(Q(impegno__gae=gae))
            .annotate(
                im_voce=F('impegno__voce__voce'),
                im_numero=F('impegno__numero'),
                im_esercizio=F('impegno__esercizio'),
                im_esorig=F('impegno__esercizio_orig'),
                im_desc=F('impegno__description'),
                im_importo=F('importo'),
                im_mandato_n=F('numero'),
                im_mandato_terzo=F('terzo'),
                im_mandato_terzo_id=F('id_terzo'),
            )
            .values(
                'im_voce',
                'im_numero',
                'im_esercizio',
                'im_esorig',
                'im_desc',
                'im_importo',
                'im_mandato_n',
                'im_mandato_terzo',
                'im_mandato_terzo_id',
            )
            .order_by('im_esorig', 'im_numero', 'im_esercizio', 'im_mandato_n')
        )

        m_act = (
            Impegno.objects
            .filter(
                Q(gae=gae) &
                Q(esercizio=datetime.date.today().year)
            )
            .annotate(
                im_voce=F('voce__voce'),
                im_numero=F('numero'),
                im_esercizio=F('esercizio'),
                im_esorig=F('esercizio_orig'),
                im_desc=F('description'),
                im_importo=F('im_competenza') + F('im_residui') - F('pagato_competenza') - F('pagato_residui'),
                im_mandato_n=ExpressionWrapper(
                    Value(0),
                    output_field=IntegerField(),
                ),
                im_mandato_terzo=ExpressionWrapper(
                    Value(""),
                    output_field=CharField(max_length=200),
                ),
                im_mandato_terzo_id=ExpressionWrapper(
                    Value(0),
                    output_field=IntegerField(),
                ),
            )
            .filter(Q(im_importo__gt=0))
            .values(
                'im_voce',
                'im_numero',
                'im_esercizio',
                'im_esorig',
                'im_desc',
                'im_importo',
                'im_mandato_n',
                'im_mandato_terzo',
                'im_mandato_terzo_id',
            )
            .order_by('im_esorig', 'im_numero', 'im_esercizio', 'im_mandato_n')
        )
        # Union
        impegni_raw = m_prev.union(m_act).order_by('im_esorig', 'im_numero', 'im_esercizio', 'im_mandato_n')

        # Group by 'numero impegno'
        impegni = {}
        for im in impegni_raw:
            tag = "{0!s}_{1!s}".format(im['im_esorig'], im['im_numero'])

            if tag not in impegni:
                impegni[tag] = {
                    'esercizio_orig': im['im_esorig'],
                    'numero': im['im_numero'],
                    'voce': im['im_voce'],
                    'desc': im['im_desc'],
                    'pagato': 0.0,
                    'dapagare': 0.0,
                    'mandati': [],
                }

            if im['im_mandato_n'] != 0:
                impegni[tag]['mandati'].append({
                    'esercizio': im['im_esercizio'],
                    'numero': im['im_mandato_n'],
                    'importo': im['im_importo'],
                    'terzo': im['im_mandato_terzo'],
                })
                impegni[tag]['pagato'] += im['im_importo']
            else:
                impegni[tag]['dapagare'] += im['im_importo']

        tot_pagato = 0.0
        tot_dapagare = 0.0
        for k, v in impegni.items():
            tot_pagato += v['pagato']
            tot_dapagare += v['dapagare']

        # impegni_raw = Impegno.objects.filter(gae=gae).order_by(
        #     'esercizio_orig', 'numero', 'esercizio')
        # impegni = {}
        # tot_pagato = 0.0
        # tot_dapagare = 0.0
        # for im in impegni_raw:
        #     tag = "{0!s}_{1!s}".format(im['im_esorig'], im['im_numero'])

        #     if tag not in impegni:
        #         impegni[tag] = {
        #             'esercizio_orig': im.esercizio_orig,
        #             'numero': im.numero,
        #             'voce': im.voce.voce,
        #             'desc': im.description,
        #             'pagato': 0.0,
        #             'dapagare': 0.0,
        #             'pks': [],
        #         }

        #     impegni[tag]['pagato'] += im.pagato_competenza + im.pagato_residui
        #     tot_pagato += im.pagato_competenza + im.pagato_residui
        #     if im.esercizio == datetime.date.today().year:
        #         impegni[tag]['dapagare'] += (im.im_competenza + im.im_residui) - (
        #             im.pagato_competenza + im.pagato_residui)
        #         tot_dapagare += (im.im_competenza + im.im_residui) - \
        #             (im.pagato_competenza + im.pagato_residui)
        #     impegni[tag]['pks'].append(im.pk)

        context = {
            'impegni': OrderedDict(sorted(impegni.items(), key=lambda x: x[0])),
            'pagato': tot_pagato,
            'dapagare': tot_dapagare,
            'impegnato': tot_pagato + tot_dapagare,
        }
        # Return formatted table through AJAX
        return render(request, 'Accounting/gae_impegni_table.html', context)


class GAEAjaxMandati(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        # Get impegno
        impegno = get_object_or_404(Impegno, pk=self.kwargs['impegno'])

        # Check GAE
        if self.only_own_gae and impegno.gae.project.pi.username != request.user:
            self.handle_no_permission()

        mandati = Mandato.objects.filter(impegno=impegno).order_by(
            'date').values('numero', 'importo', 'terzo', 'id_terzo')
        return JsonResponse(mandati)
    

class GAEAjaxDettagliMandato(PermissionRequiredMixin, View):
    permission_required = 'Accounting.gae_view'
    http_method_names = ['get', ]
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):
        # Get mandato
        mandato = get_object_or_404(Mandato, pk=self.kwargs['mandato'])

        # Check GAE
        if self.only_own_gae and mandato.impegno.gae.project.pi.username != request.user:
            self.handle_no_permission()

        # TODO: Extract fatture
        return JsonResponse()

# ============================================
# Split accounting

class SplitAccounting(PermissionRequiredMixin, ListViewMenu):
    model = SplitContab
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Accounting.splitcontab_view'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_view_own'):
            self.only_own = True
            return True
        return False

    def get_queryset(self):
        qs = (
            SplitContab.objects
            .order_by('gae')
            .values('gae')
            .distinct()
            .annotate(
                name=F('gae__name'),
                project=F('gae__project__name'),
            )
        )
        if self.only_own:
            qs = qs.filter(Q(responsible__username=self.request.user))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Split accounting"
        return context


class SplitAccountingSummaryAjax(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    only_own = False

    def has_permission(self):
        if self.request.user.has_perm('Accounting.splitcontab_view'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_view_own'):
            self.only_own = True
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Get GAE
        gae = get_object_or_404(GAE, pk=request.GET.get('gae'))

        # Extract split contab
        contabs = SplitContab.objects.filter(gae=gae)
        if self.only_own:
            contabs = contabs.filter(Q(responsible__username=self.request.user))

        # Load details
        accounting = []
        for contab in contabs:
            accounting.append({
                'contab': contab,
                'detail': create_split_accounting_detail(contab),
            })

        grand_total = {
            'stanziamento': 0,
            'variazioni': 0,
            'assestato': 0,
            'impegnato': 0,
            'residuo': 0,
        }
        for split in accounting:
            grand_total['stanziamento'] += split['detail']['totals']['stanziamento']
            grand_total['variazioni'] += split['detail']['totals']['variazioni']
            grand_total['assestato'] += split['detail']['totals']['assestato']
            grand_total['impegnato'] += split['detail']['totals']['impegnato']
            grand_total['residuo'] += split['detail']['totals']['residuo']

        context = {
            'gae': gae,
            'accounting': accounting,
            'gt': grand_total,
        }

        return render(request, 'Accounting/splitcontab_summary.html', context)


class SplitAccountingAdd(PermissionRequiredMixin, CreateViewMenu):
    model = SplitContab
    fields = ['gae', 'responsible', 'include_funding', 'notes']
    template_name = "UdyniManagement/generic_form.html"
    permission_required = 'Accounting.splitcontab_manage'

    def get_success_url(self):
        return reverse_lazy('acc_split_contab')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new splited accounting"
        context['back_url'] = self.get_success_url()
        return context


class SplitAccountingDetail(PermissionRequiredMixin, View):
    http_method_names = ['get', ]

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_view'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_view_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get(self, request, *args, **kwargs):
        # Create detailed accounting
        detail = create_split_accounting_detail(self.contab)
        split_accounting = detail['accounting']
        variazioni = detail['variazioni']
        impegni = detail['impegni']
        totals = detail['totals']
        manage = self.request.user.has_perm('Accounting.splitcontab_manage')
        manage_own = self.request.user.has_perm('Accounting.splitcontab_manage_own')
        is_owner = self.contab.responsible.username == self.request.user

        context = {
            'title': "Split accounting on GAE {0:s} (Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible),
            'contab': split_accounting,
            'contab_id': self.kwargs['pk'],
            'variazioni': variazioni,
            'impegni': impegni,
            'totals': totals,
            'menu': UdyniMenu().getMenu(request.user),
            'can_manage': manage or (manage_own and is_owner),
        }
        return render(request, 'Accounting/splitcontab_detail.html', context)


class SplitAccountingUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = SplitContab
    fields = ['include_funding', 'notes', ]
    template_name = "UdyniManagement/generic_form.html"
    permission_required = 'Accounting.splitcontab_manage'

    def get_success_url(self):
        return reverse_lazy('acc_split_contab')

    def get_context_data(self, **kwargs):
        contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify split accounting on GAE {0:s} (Resp.: {1!s})".format(contab.gae.name, contab.responsible)
        context['back_url'] = self.get_success_url()
        return context


class SplitAccountingDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = SplitContab
    template_name = "UdyniManagement/confirm_delete.html"
    permission_required = 'Accounting.splitcontab_manage'

    def get_success_url(self):
        return reverse_lazy('acc_split_contab')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete Splitted Accounting"
        context['message'] = "Are you sure you want to delete split accounting on GAE {0!s} with responsible {1!s}?".format(context['object'].gae, context['object'].researcher)
        context['back_url'] = self.get_success_url()
        return context


class SplitAccountingBudgetList(PermissionRequiredMixin, ListViewMenu):
    model = SplitBudget

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_view'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_view_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get_queryset(self):
        return SplitBudget.objects.filter(contab=self.contab)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contab'] = self.contab
        context['title'] = "Budget for split accounting on GAE {0:s} (Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        context['back_url'] = reverse_lazy('acc_split_contab_detail', kwargs={'pk': self.kwargs['pk']})
        context['budget_total'] = sum([b.importo for b in context['object_list']])
        manage = self.request.user.has_perm('Accounting.splitcontab_manage')
        manage_own = self.request.user.has_perm('Accounting.splitcontab_manage_own')
        is_owner = self.request.user == self.contab.responsible.username
        context['can_manage'] = manage or (manage_own and is_owner)
        return context


class SplitAccountingBudgetAdd(PermissionRequiredMixin, CreateViewMenu):
    model = SplitBudget
    fields = ['voce', 'year', 'importo']
    template_name = "Accounting/splitbudget_add.html"

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def form_valid(self, form):
        form.instance.contab = self.contab
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('acc_split_budget_list', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add new budget element (splitted on GAE: {0:s}  Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        context['back_url'] = self.get_success_url()
        context['stanziamenti'] = Stanziamento.objects.filter(
            gae=self.contab.gae).order_by('voce', 'esercizio')
        return context


class SplitAccountingBudgetUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = SplitBudget
    fields = ['importo', ]
    template_name = "UdyniManagement/generic_form.html"
    pk_url_kwarg = "bpk"

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get_success_url(self):
        return reverse_lazy('acc_split_budget_list', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify budget element (splitted on GAE: {0:s}  Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        context['back_url'] = self.get_success_url()
        return context


class SplitAccountingBudgetDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = SplitBudget
    template_name = "UdyniManagement/confirm_delete.html"
    pk_url_kwarg = "bpk"

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get_success_url(self):
        return reverse_lazy('acc_split_budget_list', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete budget element (splitted on GAE: {0:s}  Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        context['message'] = "Are you sure you want to remove {0:.2f} € from {1!s}, year {2:d}?".format(context['object'].importo, context['object'].voce, context['object'].year)
        context['back_url'] = self.get_success_url()
        return context


class SplitImpegniAdd(PermissionRequiredMixin, ListViewMenu):
    template_name = "Accounting/splitimpegno_add.html"

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get_queryset(self):
        im = SplitImpegno.objects.filter(Q(impegno__gae=self.contab.gae)).values_list('impegno')
        q = Impegno.objects.filter(gae=self.contab.gae).exclude(pk__in=im).order_by('esercizio_orig', 'numero', 'esercizio')
        return q

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Add impegni to splitted accounting (GAE: {0:s}  Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        context['impegni'] = self.merge_impegni(context['object_list'])
        return context

    def merge_impegni(self, impegni_raw):
        impegni = {}
        current_year = datetime.date.today().year
        for im in impegni_raw:
            label = "{0:d}_{1:d}".format(im.esercizio_orig, im.numero)
            if label not in impegni:
                impegni[label] = {
                    'esercizio_orig': im.esercizio_orig,
                    'numero': im.numero,
                    'description': im.description,
                    'voce': im.voce,
                    'importo': 0.0,
                    'pagato': 0.0,
                }

            impegni[label]['pagato'] += im.pagato_competenza
            impegni[label]['pagato'] += im.pagato_residui
            if im.esercizio < current_year:
                # Previous year, add 'pagato' to 'importo'
                impegni[label]['importo'] += im.pagato_competenza
                impegni[label]['importo'] += im.pagato_residui

            else:
                # Current year, add 'impegno' to 'importo'
                impegni[label]['importo'] += im.im_competenza
                impegni[label]['importo'] += im.im_residui

        return OrderedDict(sorted(impegni.items(), key=lambda x: x[0]))


class SplitImpegniAjax(PermissionRequiredMixin, View):
    http_method_names = ['post', ]

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def post(self, request, *args, **kwargs):
        # Init response
        response = {'result': 'ok', 'errors': []}

        # Cycle over post data and get all selected 'impegni'
        for k, v in request.POST.items():
            m = re.match("^(\d+)_(\d+)$", k)
            if m is not None:
                es = int(m.groups()[0])
                im = int(m.groups()[1])
                try:

                    # Find all the matching objects
                    impegni = Impegno.objects.filter(Q(esercizio_orig=es) & Q(numero=im))

                    # Add impegni
                    for im in impegni:
                        # NOTE: if an 'impegno' span over multiple 'esercizi' it may be alredy partially added
                        try:
                            sim = SplitImpegno.objects.get(impegno=im)
                        except SplitImpegno.DoesNotExist:
                            sim = SplitImpegno()
                            sim.contab = self.contab
                            sim.impegno = im
                            sim.save()
                except Exception as e:
                    # Failed to select and add impegni
                    response['result'] = 'fail'
                    response['errors'].append(f"Failed to add impegno {im} for esercizio {es} (Error: {e})")

        return JsonResponse(data=response)


class SplitImpegniDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = SplitBudget
    template_name = "UdyniManagement/confirm_delete.html"

    def has_permission(self):
        self.contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        if self.request.user.has_perm('Accounting.splitcontab_manage'):
            return True
        if self.request.user.has_perm('Accounting.splitcontab_manage_own') and self.contab.responsible.username == self.request.user:
            return True
        return False

    def get_object(self, queryset=None):
        # Get keyworkds from GET parameters
        try:
            esercizio = int(self.request.GET.get('esercizio'))
            numero = int(self.request.GET.get('numero'))
            voce = int(self.request.GET.get('voce'))
        except:
            raise Http404("Impegno not found")

        # Select all the objects that match the 'impegno'
        obj = (
            SplitImpegno.objects
            .filter(
                Q(contab=self.contab) &
                Q(impegno__esercizio_orig=esercizio) &
                Q(impegno__voce__voce=str(voce)) &
                Q(impegno__numero=numero)
            )
        )
        return obj

    def get_success_url(self):
        return reverse_lazy('acc_split_contab_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Remove 'impegno' from splitted accounting (GAE: {0:s}  Resp.: {1!s})".format(self.contab.gae.name, self.contab.responsible)
        numero = context['object'][0].impegno.numero
        esercizio = context['object'][0].impegno.esercizio_orig
        context['message'] = f"Are you sure you want to remove 'impegno' {numero} of 'esercizio' {esercizio}?"
        context['back_url'] = self.get_success_url()
        return context


class SplitVariazioniAdd(PermissionRequiredMixin, CreateViewMenu):
    model = SplitVariazione
    fields = ['src_contab', 'src_voce', 'dst_contab', 'dst_voce', 'importo']
    template_name = "Accounting/splitvariazione_add.html"
    permission_required = "Accounting.splitcontab_manage"

    # def form_valid(self, form):
    #     contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
    #     form.instance.src_contab = contab
    #     return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('acc_split_contab')

    # def get_voci(self):
    #     # Get 'voci' with available budget on current split accounting
    #     contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
    #     q1 = SplitBudget.objects.filter(contab=contab).values('voce').distinct()
    #     q2 = SplitVariazione.objects.filter(dst_contab=contab).annotate(voce=F('dst_voce')).values('voce').distinct()
    #     if q1:
    #         q = q1
    #         if q2:
    #             q |= q2
    #     else:
    #         q = q2
    #     return VoceSpesa.objects.filter(pk__in=q.distinct()).order_by('voce')

    def get_context_data(self, **kwargs):
        gae = get_object_or_404(GAE, pk=self.kwargs['gae'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Add 'variazione' to splitted accounting on GAE {0:s}".format(gae.name)
        context['back_url'] = self.get_success_url()
        context['gae'] = gae
        context['variazioni_split'] = (
            SplitVariazione.objects
            .filter(Q(src_contab__gae=gae) | Q(dst_contab__gae=gae))
            .order_by('src_voce', 'dst_voce', 'importo')
        )
        context['variazioni_gae'] = (
            Variazione.objects
            .filter(gae=gae)
            .order_by('voce', 'esercizio')
        )
        # Set source voce selections
        context['form'].fields['src_contab'].queryset = SplitContab.objects.filter(gae=gae).order_by('responsible')
        context['form'].fields['dst_contab'].queryset = SplitContab.objects.filter(gae=gae).order_by('responsible')
        return context


class SplitVariazioniUpdate(PermissionRequiredMixin, UpdateViewMenu):
    model = SplitVariazione
    fields = ['importo', ]
    template_name = "UdyniManagement/generic_form.html"
    permission_required = "Accounting.splitcontab_manage"

    def get_success_url(self):
        return reverse_lazy('acc_split_contab_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        contab = get_object_or_404(SplitContab, pk=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['title'] = "Modify 'variazione' to splitted accounting (GAE: {0:s}  Resp.: {1!s})".format(contab.gae.name, contab.responsible)
        context['back_url'] = self.get_success_url()
        return context


class SplitVariazioniDelete(PermissionRequiredMixin, DeleteViewMenu):
    model = SplitVariazione
    template_name = "UdyniManagement/confirm_delete.html"
    pk_url_kwarg = "vpk"
    permission_required = "Accounting.splitcontab_manage"

    def get_success_url(self):
        return reverse_lazy('acc_split_contab')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete 'variazione' to splitted accounting (GAE: {0:s})".format(context['object'].src_contab.gae.name)
        context['message'] = "Are you sure you want to remove 'variazione' from {0!s} (Voce: {1:s}) to {2!s} (Voce: {3:s})?".format(context['object'].src_contab, context['object'].src_voce.voce, context['object'].dst_contab, context['object'].dst_voce.voce)
        context['back_url'] = self.get_success_url()
        return context


# ===================
# Funding

class Funding(PermissionRequiredMixin, TemplateViewMenu):
    template_name = "Accounting/funding.html"
    permission_required = 'Accounting.gae_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Udyni Funding"

        # GAEs that do not have a splitted contab should be fully included
        stanziamenti = (
            Stanziamento.objects
            .filter(Q(gae__include_funding=True))
            .filter(~Q(gae__in=SplitContab.objects.order_by('gae').values('gae').distinct()))
            .order_by('gae', 'voce')
            .values('gae', 'voce')
            .annotate(
                tot_residuo=Coalesce(Sum('residuo'), Value(0.0)),
                gae_name=F('gae__name'),
                project=F('gae__project__name'),
                voce_num=F('voce__voce'),
                voce_desc=F('voce__description'),
            )
        )

        # Add residui to funding
        all_projects = []
        voce_desc = {}
        funding = {}
        for s in stanziamenti:
            if s['tot_residuo'] != 0.0:
                voce = s['voce_num']
                if voce not in funding:
                    funding[voce] = {}
                    voce_desc[voce] = s['voce_desc']

                prj = s['project']
                if prj not in all_projects:
                    all_projects.append(prj)
                if prj not in funding[voce]:
                    funding[voce][s['project']] = s['tot_residuo']
                else:
                    print("Dupicated project", prj)

        # Residui on splitted contab
        splitted = SplitContab.objects.filter(include_funding=True).order_by('gae')
        for contab in splitted:
            detail = create_split_accounting_detail(contab)

            for voce, s in detail['accounting'].items():
                if s['residuo'] != 0.0:
                    if voce not in funding:
                        funding[voce] = {}
                        voce_desc[voce] = s['desc']

                    prj = contab.gae.project.name
                    if prj not in all_projects:
                        all_projects.append(prj)
                    if prj not in funding[voce]:
                        funding[voce][prj] = s['residuo']
                    else:
                        print("Dupicated project", prj, s)

        context['voce_desc'] = voce_desc
        context['all_projects'] = sorted(all_projects)
        context['funding'] = OrderedDict()
        context['totals_by_project'] = {}
        context['totals_by_voce'] = {}
        context['grand_total'] = 0.0
        for k in sorted(funding.keys()):
            if len(funding[k]):
                context['funding'][k] = funding[k]
                for prj, residuo in funding[k].items():
                    if prj not in context['totals_by_project']:
                        context['totals_by_project'][prj] = 0.0
                    if k not in context['totals_by_voce']:
                        context['totals_by_voce'][k] = 0.0
                    context['totals_by_project'][prj] += residuo
                    context['totals_by_voce'][k] += residuo
                    context['grand_total'] += residuo

        return context
