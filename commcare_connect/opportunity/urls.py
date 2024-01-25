from django.urls import path

from commcare_connect.opportunity.views import (
    OpportunityCreate,
    OpportunityDeliverStatusTable,
    OpportunityDetail,
    OpportunityEdit,
    OpportunityList,
    OpportunityPaymentTableView,
    OpportunityPaymentUnitTableView,
    OpportunityUserLearnProgress,
    OpportunityUserStatusTableView,
    OpportunityUserTableView,
    UserPaymentsTableView,
    add_budget_existing_users,
    add_payment_unit,
    download_export,
    edit_payment_unit,
    export_deliver_status,
    export_status,
    export_user_status,
    export_user_visits,
    export_users_for_payment,
    payment_delete,
    payment_import,
    send_message_mobile_users,
    update_visit_status_import,
    user_visits_list,
)

app_name = "opportunity"
urlpatterns = [
    path("", view=OpportunityList.as_view(), name="list"),
    path("create/", view=OpportunityCreate.as_view(), name="create"),
    path("<int:pk>/edit", view=OpportunityEdit.as_view(), name="edit"),
    path("<int:pk>/", view=OpportunityDetail.as_view(), name="detail"),
    path("<int:pk>/user_table/", view=OpportunityUserTableView.as_view(), name="user_table"),
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
    path("<int:pk>/payment_unit_table/", view=OpportunityPaymentUnitTableView.as_view(), name="payment_unit_table"),
    path("<int:opp_id>/payment_unit/<int:pk>/edit", view=edit_payment_unit, name="edit_payment_unit"),
    path("<int:opp_id>/user_payment_table/<int:pk>", view=UserPaymentsTableView.as_view(), name="user_payments_table"),
    path("<int:pk>/user_status_export/", view=export_user_status, name="user_status_export"),
    path("<int:pk>/deliver_status_table/", view=OpportunityDeliverStatusTable.as_view(), name="deliver_status_table"),
    path("<int:pk>/deliver_status_export/", view=export_deliver_status, name="deliver_status_export"),
    path("<int:opp_id>/user_visits/<int:pk>/", view=user_visits_list, name="user_visits_list"),
    path("<int:opp_id>/payment/<int:access_id>/delete/<int:pk>/", view=payment_delete, name="payment_delete"),
    path("<int:pk>/send_message", view=send_message_mobile_users, name="send_message_mobile_users"),
]
