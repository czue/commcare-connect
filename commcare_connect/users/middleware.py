from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

from .helpers import get_organization_for_request
from .models import UserOrganizationMembership as Membership


def _get_organization(request, view_kwargs):
    if not hasattr(request, '_cached_org'):
        team = get_organization_for_request(request, view_kwargs)
        request._cached_org = team
    return request._cached_org


def _get_org_membership(request):
    if not hasattr(request, '_cached_org_membership'):
        org = request.org
        membership = None
        if org:
            try:
                membership = Membership.objects.get(organization=org, user=request.user) if org else None
            except Membership.DoesNotExist:
                pass
        request._cached_org_membership = membership
    return request._cached_org_membership


class OrganizationMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request.org = SimpleLazyObject(lambda: _get_organization(request, view_kwargs))
        request.org_membership = SimpleLazyObject(lambda: _get_org_membership(request))
