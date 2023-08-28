from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Field, Row, Submit
from django import forms
from django.utils.timezone import now

from commcare_connect.opportunity.models import CommCareApp, DeliverForm, HQApiKey, Opportunity
from commcare_connect.organization.models import Organization


class OpportunityChangeForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ["name", "description", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(Field("name")),
            Row(Field("description")),
            Row(Field("active")),
            Submit("submit", "Submit"),
        )


class OpportunityCreationForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            "name",
            "description",
            "end_date",
            "max_visits_per_user",
            "daily_max_visits_per_user",
            "budget_per_visit",
            "total_budget",
        ]
        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.applications = kwargs.pop("applications", [])
        self.user = kwargs.pop("user", {})
        self.org_slug = kwargs.pop("org_slug", "")
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(Field("name")),
            Row(Field("description")),
            Row(Field("end_date")),
            Row(
                Field("max_visits_per_user", wrapper_class="form-group col-md-6 mb-0"),
                Field("daily_max_visits_per_user", wrapper_class="form-group col-md-6 mb-0"),
            ),
            Row(
                Field("total_budget", wrapper_class="form-group col-md-6 mb-0"),
                Field("budget_per_visit", wrapper_class="form-group col-md-6 mb-0"),
            ),
            Row(Field("learn_app")),
            Row(Field("learn_app_description")),
            Row(Field("learn_app_passing_score")),
            Row(Field("deliver_app")),
            Row(Field("deliver_form")),
            Row(Field("api_key")),
            Submit("submit", "Submit"),
        )

        app_choices = []
        form_choices = []
        for app in self.applications:
            app_choices.append((app["id"], app["name"]))
            for form in app["forms"]:
                form_choices.append((form["id"], form["name"]))

        self.fields["learn_app"] = forms.ChoiceField(choices=app_choices)
        self.fields["learn_app_description"] = forms.CharField(widget=forms.Textarea)
        self.fields["learn_app_passing_score"] = forms.IntegerField(max_value=100, min_value=0)
        self.fields["deliver_app"] = forms.ChoiceField(choices=app_choices)
        self.fields["deliver_app"].widget.attrs.update({"id": "deliver_app_select"})
        self.fields["deliver_form"] = forms.ChoiceField(choices=form_choices)
        self.fields["deliver_form"].widget.attrs.update({"id": "deliver_form_select"})
        self.fields["api_key"] = forms.CharField(max_length=50)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data:
            if cleaned_data["learn_app"] == cleaned_data["deliver_app"]:
                self.add_error("learn_app", "Learn app and Deliver app cannot be same")
                self.add_error("deliver_app", "Learn app and Deliver app cannot be same")

            if cleaned_data["daily_max_visits_per_user"] > cleaned_data["max_visits_per_user"]:
                self.add_error(
                    "daily_max_visits_per_user",
                    "Daily max visits per user cannot be greater than Max visits per user",
                )

            if cleaned_data["budget_per_visit"] > cleaned_data["total_budget"]:
                self.add_error("budget_per_visit", "Budget per visit cannot be greater than Total budget")

            if cleaned_data["end_date"] < now().date():
                self.add_error("end_date", "Please enter the correct end date for this opportunity")

    def save(self, commit=True):
        organization = Organization.objects.filter(slug=self.org_slug).first()
        deliver_form = DeliverForm()

        for app in self.applications:
            if app["id"] == self.cleaned_data["learn_app"]:
                self.instance.learn_app, _ = CommCareApp.objects.get_or_create(
                    cc_app_id=app["id"],
                    cc_domain=app["domain"],
                    organization=organization,
                    defaults={
                        "name": app["name"],
                        "created_by": self.user.email,
                        "modified_by": self.user.email,
                        "description": self.cleaned_data["learn_app_description"],
                        "passing_score": self.cleaned_data["learn_app_passing_score"],
                    },
                )

            if app["id"] == self.cleaned_data["deliver_app"]:
                self.instance.deliver_app, _ = CommCareApp.objects.get_or_create(
                    cc_app_id=app["id"],
                    cc_domain=app["domain"],
                    organization=organization,
                    defaults={
                        "name": app["name"],
                        "created_by": self.user.email,
                        "modified_by": self.user.email,
                    },
                )

                for form in app["forms"]:
                    if form["id"] == self.cleaned_data["deliver_form"]:
                        deliver_form.xmlns = form["xmlns"]
                        deliver_form.name = form["name"]
                        deliver_form.app = self.instance.deliver_app

        self.instance.created_by = self.user.email
        self.instance.modified_by = self.user.email
        self.instance.organization = organization

        api_key, _ = HQApiKey.objects.get_or_create(user=self.user, api_key=self.cleaned_data["api_key"])
        self.instance.api_key = api_key
        super().save(commit=commit)

        deliver_form.opportunity = self.instance
        deliver_form.clean()
        deliver_form.save()

        return self.instance
