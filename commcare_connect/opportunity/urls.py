from django.urls import path

from commcare_connect.opportunity.views import (
    OpportunityCompletedWorkTable,
    OpportunityCreate,
    OpportunityDeliverStatusTable,
    OpportunityDetail,
    OpportunityEdit,
    OpportunityFinalize,
    OpportunityInit,
    OpportunityLearnStatusTableView,
    OpportunityList,
    OpportunityPaymentTableView,
    OpportunityPaymentUnitTableView,
    OpportunityUserLearnProgress,
    OpportunityUserStatusTableView,
    UserPaymentsTableView,
    add_budget_existing_users,
    add_payment_unit,
    add_payment_units,
    approve_visit,
    download_export,
    edit_payment_unit,
    export_completed_work,
    export_deliver_status,
    export_status,
    export_user_status,
    export_user_visits,
    export_users_for_payment,
    fetch_attachment,
    get_application,
    payment_delete,
    payment_import,
    reject_visit,
    send_message_mobile_users,
    update_completed_work_status_import,
    update_visit_status_import,
    user_profile,
    user_visits_list,
    visit_verification,
)

app_name = "opportunity"
urlpatterns = [
    path("", view=OpportunityList.as_view(), name="list"),
    path("create/", view=OpportunityCreate.as_view(), name="create"),
    path("init/", view=OpportunityInit.as_view(), name="init"),
    path("<int:pk>/finalize/", view=OpportunityFinalize.as_view(), name="finalize"),
    path("<int:pk>/edit", view=OpportunityEdit.as_view(), name="edit"),
    path("<int:pk>/", view=OpportunityDetail.as_view(), name="detail"),
    path("<int:pk>/user_table/", view=OpportunityLearnStatusTableView.as_view(), name="user_table"),
    path("<int:pk>/user_status_table/", view=OpportunityUserStatusTableView.as_view(), name="user_status_table"),
    path("<int:pk>/visit_export/", view=export_user_visits, name="visit_export"),
    path("export_status/<slug:task_id>", view=export_status, name="export_status"),
    path("download_export/<slug:task_id>", view=download_export, name="download_export"),
    path("<int:pk>/visit_import/", view=update_visit_status_import, name="visit_import"),
    path(
        "<int:opp_id>/learn_progress/<int:pk>",
        view=OpportunityUserLearnProgress.as_view(),
        name="user_learn_progress",
    ),
    path(
        "<int:pk>/add_budget_existing_users",
        view=add_budget_existing_users,
        name="add_budget_existing_users",
    ),
    path("<int:pk>/payment_table/", view=OpportunityPaymentTableView.as_view(), name="payment_table"),
    path("<int:pk>/payment_export/", view=export_users_for_payment, name="payment_export"),
    path("<int:pk>/payment_import/", view=payment_import, name="payment_import"),
    path("<int:pk>/payment_unit/create", view=add_payment_unit, name="add_payment_unit"),
    path("<int:pk>/payment_units/create", view=add_payment_units, name="add_payment_units"),
    path("<int:pk>/payment_unit_table/", view=OpportunityPaymentUnitTableView.as_view(), name="payment_unit_table"),
    path("<int:opp_id>/payment_unit/<int:pk>/edit", view=edit_payment_unit, name="edit_payment_unit"),
    path("<int:opp_id>/user_payment_table/<int:pk>", view=UserPaymentsTableView.as_view(), name="user_payments_table"),
    path("<int:pk>/user_status_export/", view=export_user_status, name="user_status_export"),
    path("<int:pk>/deliver_status_table/", view=OpportunityDeliverStatusTable.as_view(), name="deliver_status_table"),
    path("<int:pk>/deliver_status_export/", view=export_deliver_status, name="deliver_status_export"),
    path("<int:opp_id>/user_visits/<int:pk>/", view=user_visits_list, name="user_visits_list"),
    path("<int:opp_id>/payment/<int:access_id>/delete/<int:pk>/", view=payment_delete, name="payment_delete"),
    path("<int:opp_id>/user_profile/<int:pk>/", view=user_profile, name="user_profile"),
    path("<int:pk>/send_message", view=send_message_mobile_users, name="send_message_mobile_users"),
    path("applications/", get_application, name="get_applications_by_domain"),
    path("verification/<int:pk>/", view=visit_verification, name="visit_verification"),
    path("approve/<int:pk>/", view=approve_visit, name="approve_visit"),
    path("reject/<int:pk>/", view=reject_visit, name="reject_visit"),
    path("fetch_attachment/<blob_id>", view=fetch_attachment, name="fetch_attachment"),
    path("<int:pk>/completed_work_table/", view=OpportunityCompletedWorkTable.as_view(), name="completed_work_table"),
    path("<int:pk>/completed_work_export/", view=export_completed_work, name="completed_work_export"),
    path("<int:pk>/completed_work_import/", view=update_completed_work_status_import, name="completed_work_import"),
]
