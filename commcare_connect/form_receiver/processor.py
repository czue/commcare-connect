from jsonpath_ng import JSONPathError
from jsonpath_ng.ext import parse

from commcare_connect.form_receiver.const import CCC_LEARN_XMLNS
from commcare_connect.form_receiver.exceptions import ProcessingError
from commcare_connect.form_receiver.serializers import XForm
from commcare_connect.opportunity.models import (
    Assessment,
    CommCareApp,
    CompletedModule,
    DeliverForm,
    LearnModule,
    Opportunity,
    UserVisit,
)
from commcare_connect.users.models import User

LEARN_MODULE_JSONPATH = parse("$..module")
ASSESSMENT_JSONPATH = parse("$..assessment")


def process_xform(xform: XForm):
    """Process a form received from CommCare HQ."""
    app = get_app(xform.domain, xform.app_id)
    user = get_user(xform)

    if process_deliver_form(user, xform):
        return

    opportunity = get_opportunity_for_learn_app(app)
    if not opportunity:
        raise ProcessingError(f"No active opportunities found for CommCare app {app.cc_app_id}.")
    process_learn_form(user, xform, app, opportunity)


def process_learn_form(user, xform: XForm, app: CommCareApp, opportunity: Opportunity):
    processors = [
        (LEARN_MODULE_JSONPATH, process_learn_modules),
        (ASSESSMENT_JSONPATH, process_assessments),
    ]
    for jsonpath, processor in processors:
        try:
            matches = [match.value for match in jsonpath.find(xform.form) if match.value["@xmlns"] == CCC_LEARN_XMLNS]
            if matches:
                processor(user, xform, app, opportunity, matches)
        except JSONPathError as e:
            raise ProcessingError from e


def get_or_create_learn_module(app, module_data):
    module, _ = LearnModule.objects.get_or_create(
        app=app,
        slug=module_data["@id"],
        defaults=dict(
            name=module_data["name"],
            description=module_data["description"],
            time_estimate=module_data["time_estimate"],
        ),
    )
    return module


def process_learn_modules(user, xform: XForm, app: CommCareApp, opportunity: Opportunity, blocks: list[dict]):
    """Process learn modules from a form received from CommCare HQ.

    :param user: The user who submitted the form.
    :param xform: The deserialized form object.
    :param app: The CommCare app the form belongs to.
    :param opportunity: The opportunity the app belongs to.
    :param blocks: A list of learn module form blocks."""
    for module_data in blocks:
        module = get_or_create_learn_module(app, module_data)
        completed_module, created = CompletedModule.objects.get_or_create(
            user=user,
            module=module,
            opportunity=opportunity,
            xform_id=xform.id,
            defaults={
                "date": xform.received_on,
                "duration": xform.metadata.duration,
                "app_build_id": xform.build_id,
                "app_build_version": xform.metadata.app_build_version,
            },
        )

        if not created:
            raise ProcessingError("Learn Module is already completed")


def process_assessments(user, xform: XForm, app: CommCareApp, opportunity: Opportunity, blocks: list[dict]):
    """Process assessments from a form received from CommCare HQ.

    :param user: The user who submitted the form.
    :param xform: The deserialized form object.
    :param app: The CommCare app the form belongs to.
    :param opportunity: The opportunity the app belongs to.
    :param blocks: A list of assessment form blocks."""
    for assessment_data in blocks:
        try:
            score = int(assessment_data["user_score"])
        except ValueError:
            raise ProcessingError("User score must be an integer")
        # TODO: should this move to the opportunity to allow better re-use of the app?
        passing_score = app.passing_score
        assessment, created = Assessment.objects.get_or_create(
            user=user,
            app=app,
            opportunity=opportunity,
            xform_id=xform.id,
            defaults={
                "date": xform.received_on,
                "score": score,
                "passing_score": passing_score,
                "passed": score >= passing_score,
                "app_build_id": xform.build_id,
                "app_build_version": xform.metadata.app_build_version,
            },
        )

        if not created:
            return ProcessingError("Learn Assessment is already completed")


def process_deliver_form(user, xform):
    try:
        deliver_form = DeliverForm.objects.filter(
            xmlns=xform.xmlns, app__cc_domain=xform.domain, app__cc_app_id=xform.app_id
        ).get()
    except DeliverForm.DoesNotExist:
        return False
    except DeliverForm.MultipleObjectsReturned:
        raise ProcessingError(f"Multiple deliver forms found for this app and XMLNS: {xform.app_id}, {xform.xmlns}")

    UserVisit.objects.create(
        opportunity=deliver_form.opportunity,
        user=user,
        deliver_form=deliver_form,
        visit_date=xform.metadata.timeStart,
        xform_id=xform.id,
        app_build_id=xform.build_id,
        app_build_version=xform.metadata.app_build_version,
        form_json=xform.raw_form,
    )
    return True


def get_opportunity_for_learn_app(app):
    try:
        return Opportunity.objects.get(learn_app=app, active=True)
    except Opportunity.DoesNotExist:
        pass
    except Opportunity.MultipleObjectsReturned:
        raise ProcessingError(f"Multiple active opportunities found for CommCare app {app.cc_app_id}.")


def get_app(domain, app_id):
    app = CommCareApp.objects.filter(cc_domain=domain, cc_app_id=app_id).first()
    if not app:
        raise ProcessingError(f"CommCare app {app_id} not found.")
    return app


def get_user(xform: XForm):
    cc_username = _get_commcare_username(xform)
    user = User.objects.filter(connectiduserlink__commcare_username=cc_username).first()
    if not user:
        raise ProcessingError(f"Commcare User {cc_username} not found")
    return user


def _get_commcare_username(xform: XForm):
    username = xform.metadata.username
    if "@" in username:
        return username
    return f"{username}@{xform.domain}.commcarehq.org"
