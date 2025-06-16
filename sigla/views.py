import re
import time
import datetime
import traceback
import json
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.views import View
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.mixins import PermissionRequiredMixin

from UdyniManagement.menu import UdyniMenu

from sigla.sigla import SIGLA

from Accounting.models import GAE


# Create your views here.
class SiglaManualView(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_manage'

    def get(self, request, *args, **kwargs):

        context = {
            'title': "SIGLA REST API Manual",
            'menu': UdyniMenu().getMenu(request.user),
            'error': False,
        }

        # Get info.json
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)
        try:
            data = s.getRequest("info.json")

            pages = {}
            for page in data:
                url = page['action'][1:]
                pages[url] = {
                    'descrizione': page['descrizione'] if 'descrizione' in page else 'No description',
                    'permessi': page['accesso'] if 'accesso' in page else 'No permissions',
                    'auth': True if page['authentication'].lower() == 'true' else False,
                }

            context['elements'] = pages
        except Exception as e:
            context['error'] = True
            context['message'] = "{0!s}: {1!s}".format(type(e).__name__, e)

        return render(request, 'sigla/manual_main.html', context)


class SiglaAjaxManualView(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_manage'

    def get(self, request, *args, **kwargs):

        response = {'error': False}

        # Action
        if 'action' in request.GET:
            action = re.sub(r'\W+', '', request.GET['action'])

            s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)
            try:
                data = s.getRequest("{0:s}.json".format(action))
                response['data'] = data
            except Exception as e:
                response['error'] = True
                response['message'] = "{0!s}: {1!s}".format(type(e).__name__, e)
        else:
            response['error'] = True
            response['message'] = 'Must provide an action'

        return JsonResponse(response)


class SiglaProgetti(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Projects.project_manage'

    def get(self, request, *args, **kwargs):

        # Check if we have recent cached data in session
        projects, last_update = request.session.get('sigla_progetti', (None, 0))

        if projects is None or time.time() - last_update > 600:
            # No value cached or cached value expired
            if settings.DEBUG:
                print("Cache expired on {0:s}".format(datetime.datetime.fromtimestamp(last_update).isoformat()))
            try:
                # Get data from SIGLA
                s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)
                projects = s.getProgetti()
                last_update = time.time()
                # Encode to JSON and store in session
                en = DjangoJSONEncoder()
                request.session['sigla_progetti'] = (en.encode(projects), last_update)

            except Exception as e:
                response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}
                return JsonResponse(response)

        else:
            if settings.DEBUG:
                print("Using data chached on {0:s}".format(datetime.datetime.fromtimestamp(last_update).isoformat()))
            # Decode json
            projects = json.loads(projects, object_hook=self.__decode_date)

        response = {'error': False, 'elements': projects}
        return JsonResponse(response)

    def __decode_date(self, dct):
        for k, v in dct.items():
            if type(v) is str:
                m = re.match(r"^(\d+)-(\d+)-(\d+)$", v)
                if m is not None:
                    dct[k] = datetime.date(int(m.groups()[0]), int(m.groups()[1]), int(m.groups()[2]))
        return dct


class SiglaGAE(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_manage'

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            gae = s.getGAE(self.kwargs['pg_progetto'])
            response = {'error': False, 'elements': gae}

        except Exception as e:
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaGAECompetenza(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            esercizio = self.kwargs['esercizio']
        except:
            esercizio = datetime.date.today().year

        # Check gae
        if self.only_own_gae:
            gae = get_object_or_404(GAE, name=self.kwargs['gae'])
            if gae.project.pi.username != request.user:
                self.handle_no_permission()

        try:
            gae = s.getCompetenza(self.kwargs['gae'], esercizio)
            response = {'error': False, 'elements': gae}

        except Exception as e:
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaGAEResidui(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'
    only_own_gae = False

    def has_permission(self):
        p = super().has_permission()
        if not p and self.request.user.has_perm('Accounting.gae_view_own'):
            self.only_own_gae = True
            return True
        return p

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        # Check gae
        if self.only_own_gae:
            gae = get_object_or_404(GAE, name=self.kwargs['gae'])
            if gae.project.pi.username != request.user:
                self.handle_no_permission()

        try:
            gae = s.getResidui(self.kwargs['gae'])
            response = {'error': False, 'elements': gae}

        except Exception as e:
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaGAEImpegni(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            esercizio = self.kwargs['esercizio']
        except:
            esercizio = datetime.date.today().year

        try:
            impegni = s.getImpegni(self.kwargs['gae'], esercizio)
            response = {'error': False, 'elements': impegni}

        except Exception as e:
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaGAEVariazioni(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            esercizio = self.kwargs['esercizio']
        except:
            esercizio = datetime.date.today().year

        try:
            variazioni = s.getVariazioni(self.kwargs['gae'], esercizio)
            response = {'error': False, 'elements': variazioni}

        except Exception as e:
            traceback.print_exc()
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaMandati(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            esercizio = self.kwargs['esercizio']
        except:
            esercizio = datetime.date.today().year

        try:
            mandati = s.getMandati(self.kwargs['pg_obb'], self.kwargs['es_orig'], esercizio)
            response = {'error': False, 'elements': mandati}

        except Exception as e:
            traceback.print_exc()
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)


class SiglaFatture(PermissionRequiredMixin, View):
    http_method_names = ['get', ]
    permission_required = 'Accounting.GAE_view'

    def get(self, request, *args, **kwargs):

        # Sigla interface
        s = SIGLA(settings.SIGLA_USERNAME, settings.SIGLA_PASSWORD)

        try:
            esercizio = self.kwargs['esercizio']
        except:
            esercizio = datetime.date.today().year

        try:
            fatture = s.getFatture(self.kwargs['pg_mandato'], esercizio)
            response = {'error': False, 'elements': fatture}

        except Exception as e:
            traceback.print_exc()
            response = {'error': True, 'message': "{0!s}: {1!s}".format(type(e).__name__, e)}

        return JsonResponse(response)
