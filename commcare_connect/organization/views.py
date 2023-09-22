from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext
from rest_framework.decorators import api_view

from commcare_connect.organization.decorators import org_admin_required
from commcare_connect.organization.forms import OrganizationChangeForm, UserOrganizationMembershipFormset
from commcare_connect.organization.models import Organization, UserOrganizationMembership


@org_admin_required
def organization_home(request, org_slug):
    org = get_object_or_404(Organization, slug=org_slug)

    form = None
    if request.method == "POST":
        form = OrganizationChangeForm(request.POST, instance=org)
        if form.is_valid():
            messages.success(request, gettext("Organization details saved!"))
            form.save()

    if not form:
        form = OrganizationChangeForm(instance=org)

    return render(
        request,
        "organization/organization_home.html",
        {
            "organization": org,
            "form": form,
        },
    )


@api_view(["POST"])
@login_required
def add_members_form(request, org_slug):
    org = get_object_or_404(Organization, slug=org_slug)
    formset = UserOrganizationMembershipFormset()

    for form in formset:
        if form.is_valid():
            form.instance.organization = org
            form.save()
    if formset.is_valid():
        formset.save()
    else:
        messages.error(request, message=formset.error_messages)
    return redirect(reverse("organization:home", args=(org_slug,)))


@login_required
def accept_invite(request, invite_id):
    membership = get_object_or_404(UserOrganizationMembership, invite_id=invite_id)
    organization = membership.organization

    if membership.accepted:
        return redirect(reverse("organization:home", args=(organization.slug,)))

    membership.accepted = True
    membership.save()
    messages.success(request, message=f"Accepted invite for joining {organization.slug} organization.")
    return redirect("organization:home", args=(organization.slug,))
