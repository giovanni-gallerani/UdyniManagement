import logging
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from UdyniManagement.menu import UdyniMenu


# =============================================
# MAIN INDEX VIEW

class EmptyView(LoginRequiredMixin, View):
    http_method_names = ['get', ]

    def get(self, request, *args, **kwargs):
        context = {
            'title': "Welcome!",
            'menu': UdyniMenu().getMenu(request.user),
        }
        return render(request, 'UdyniManagement/page.html', context)

# =============================================
# SERVICE MIXINS

class AjaxPermissionRequiredMixin(PermissionRequiredMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied as e:
            rsp = JsonResponse(data={'status': 'error', 'message': str(e)})
            rsp.status_code = 403
            return rsp
        except Http404 as e:
            rsp = JsonResponse(data={'status': 'error', 'message': str(e)})
            rsp.status_code = 404
            return rsp
        except Exception:
            log = logging.getLogger('django')
            log.exception('Ajax serve failed with exception')
            rsp = JsonResponse(data={'status': 'error', 'message': 'Internal server error. Contact administrator'})
            rsp.status_code = 500
            return rsp

class ObjectValidationMixin:
    input_objects = {}
    is_ajax_view = False

    def dispatch(self, request, *args, **kwargs):
        for k, v in self.input_objects.items():
            try:
                obj = v['class'].objects.get(pk=self.kwargs[v['pk']])
                setattr(self, k, obj)
            except v['class'].DoesNotExist:
                msg = f"{v['class'].__name__} with pk {v['pk']} does not exist"
                if self.is_ajax_view:
                    rsp = JsonResponse(data={'status': 'error', 'message': msg})
                    rsp.status_code = 400
                    return rsp
                else:
                    raise Http404(msg)
        return super().dispatch(request, *args, **kwargs)


# =============================================
# EXTENDED VIEWS WITH MENU
class UdyniDefaultMixin(object):
    def get_title(self):
        if hasattr(self, 'title'):
            return self.title
        else:
            return ''

    def get_back_url(self):
        if hasattr(self, 'get_success_url'):
            return self.get_success_url()
        else:
            return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = UdyniMenu().getMenu(self.request.user)
        context['title'] = self.get_title()
        context['back_url'] = self.get_back_url()
        return context

class TemplateViewMenu(UdyniDefaultMixin, TemplateView):
    pass

class ListViewMenu(UdyniDefaultMixin, ListView):
    pass

class DetailViewMenu(UdyniDefaultMixin, DetailView):
    pass

class CreateViewMenu(UdyniDefaultMixin, CreateView):
    pass

class UpdateViewMenu(UdyniDefaultMixin, UpdateView):
    pass

class DeleteViewMenu(UdyniDefaultMixin, DeleteView):
    pass

class FormViewMenu(UdyniDefaultMixin, FormView):
    pass


# HTTP Error views
def udyni_404_view(request, exception):
    context = {'exception': exception}
    if request.user.is_authenticated:
        context['menu'] = UdyniMenu().getMenu(request.user)
        response = render(request, '404_user.html', context)
    else:
        response = render(request, '404.html', context)
    response.status_code = 404
    return response

def udyni_403_view(request, exception):
    context = {'exception': exception}
    if request.user.is_authenticated:
        context['menu'] = UdyniMenu().getMenu(request.user)
        response = render(request, '403_user.html', context)
    else:
        response = render(request, '403.html', context)
    response.status_code = 403
    return response


# Generic error view
def udyni_error_view(request, error_message):
    context = {
        'error': error_message,
        'menu': UdyniMenu().getMenu(request.user),
    }
    return render(request, 'UdyniManagement/error.html', context)
