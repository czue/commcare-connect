import codecs
import mimetypes
import textwrap
from dataclasses import dataclass
from decimal import Decimal

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from tablib import Dataset

from commcare_connect.opportunity.models import (
    CatchmentArea,
    CompletedWork,
    CompletedWorkStatus,
    Opportunity,
    OpportunityAccess,
    Payment,
    UserVisit,
    VisitValidationStatus,
)
from commcare_connect.opportunity.tasks import send_payment_notification
from commcare_connect.utils.file import get_file_extension
from commcare_connect.utils.itertools import batched

VISIT_ID_COL = "visit id"
STATUS_COL = "status"
USERNAME_COL = "username"
AMOUNT_COL = "payment amount"
REASON_COL = "rejected reason"
WORK_ID_COL = "instance id"
PAYMENT_APPROVAL_STATUS_COL = "payment approval"
REQUIRED_COLS = [VISIT_ID_COL, STATUS_COL]
LATITUDE_COL = "latitude"
LONGITUDE_COL = "longitude"
RADIUS_COL = "radius"
AREA_NAME_COL = "name"
ACTIVE_COL = "active"
CATCHMENT_ID = "catchment id"


class ImportException(Exception):
    def __init__(self, message, rows=None):
        self.message = message
        self.rows = rows


@dataclass
class VisitImportStatus:
    seen_visits: set[str]
    missing_visits: set[str]

    def __len__(self):
        return len(self.seen_visits)

    def get_missing_message(self):
        joined = ", ".join(self.missing_visits)
        missing = textwrap.wrap(joined, width=115, break_long_words=False, break_on_hyphens=False)
        return f"<br>{len(self.missing_visits)} visits were not found:<br>{'<br>'.join(missing)}"


@dataclass
class PaymentImportStatus:
    seen_users: set[str]
    missing_users: set[str]

    def __len__(self):
        return len(self.seen_users)

    def get_missing_message(self):
        joined = ", ".join(self.missing_users)
        missing = textwrap.wrap(joined, width=115, break_long_words=False, break_on_hyphens=False)
        return f"<br>{len(self.missing_users)} usernames were not found:<br>{'<br>'.join(missing)}"


@dataclass
class CompletedWorkImportStatus:
    seen_completed_works: set[str]
    missing_completed_works: set[str]

    def __len__(self):
        return len(self.seen_completed_works)

    def get_missing_message(self):
        joined = ", ".join(self.missing_completed_works)
        missing = textwrap.wrap(joined, width=115, break_long_words=False, break_on_hyphens=False)
        return f"<br>{len(self.missing_completed_works)} completed works were not found:<br>{'<br>'.join(missing)}"


@dataclass
class CatchmentAreaImportStatus:
    seen_catchment_area: set[str]
    missing_catchment_area: set[str]

    def __len__(self):
        return len(self.seen_catchment_area)

    def get_missing_message(self):
        joined = ", ".join(self.missing_catchment_area)
        missing = textwrap.wrap(joined, width=115, break_long_words=False, break_on_hyphens=False)
        return f"<br>{len(self.missing_catchment_area)} catchment areas had error:<br>{'<br>'.join(missing)}"


def bulk_update_visit_status(opportunity: Opportunity, file: UploadedFile) -> VisitImportStatus:
    file_format = None
    if file.content_type:
        file_format = mimetypes.guess_extension(file.content_type)
        if file_format:
            file_format = file_format[1:]
    if not file_format:
        file_format = file.name.split(".")[-1].lower()
    if file_format not in ("csv", "xlsx"):
        raise ImportException(f"Invalid file format. Only 'CSV' and 'XLSX' are supported. Got {file_format}")
    imported_data = get_imported_dataset(file, file_format)
    return _bulk_update_visit_status(opportunity, imported_data)


def _bulk_update_visit_status(opportunity: Opportunity, dataset: Dataset):
    status_by_visit_id, reasons_by_visit_id = get_status_by_visit_id(dataset)
    visit_ids = list(status_by_visit_id)
    missing_visits = set()
    seen_visits = set()
    user_ids = set()
    seen_completed_works = set()
    with transaction.atomic():
        for visit_batch in batched(visit_ids, 100):
            to_update = []
            visits = UserVisit.objects.filter(xform_id__in=visit_batch, opportunity=opportunity)
            for visit in visits:
                seen_visits.add(visit.xform_id)
                seen_completed_works.add(visit.completed_work_id)
                status = status_by_visit_id[visit.xform_id]
                if visit.status != status:
                    visit.status = status
                    reason = reasons_by_visit_id.get(visit.xform_id)
                    if visit.status == VisitValidationStatus.rejected and reason:
                        visit.reason = reason
                    to_update.append(visit)
                user_ids.add(visit.user_id)

            UserVisit.objects.bulk_update(to_update, fields=["status", "reason"])
            missing_visits |= set(visit_batch) - seen_visits
    update_payment_accrued(opportunity, users=user_ids)

    return VisitImportStatus(seen_visits, missing_visits)


def update_payment_accrued(opportunity: Opportunity, users):
    """Updates payment accrued for completed and approved CompletedWork instances."""
    access_objects = OpportunityAccess.objects.filter(user__in=users, opportunity=opportunity, suspended=False)
    for access in access_objects:
        completed_works = access.completedwork_set.exclude(
            status__in=[CompletedWorkStatus.rejected, CompletedWorkStatus.over_limit]
        ).select_related("payment_unit")
        access.payment_accrued = 0
        for completed_work in completed_works:
            # Auto Approve Payment conditions
            if completed_work.completed_count > 0:
                if opportunity.auto_approve_payments:
                    visits = completed_work.uservisit_set.values_list("status", "reason")
                    if any(status == "rejected" for status, _ in visits):
                        completed_work.status = CompletedWorkStatus.rejected
                        completed_work.reason = "\n".join(reason for _, reason in visits if reason)
                    elif all(status == "approved" for status, _ in visits):
                        completed_work.status = CompletedWorkStatus.approved
                approved_count = completed_work.approved_count
                if approved_count > 0 and completed_work.status == CompletedWorkStatus.approved:
                    access.payment_accrued += approved_count * completed_work.payment_unit.amount
                completed_work.save()
        access.save()


def get_status_by_visit_id(dataset) -> dict[int, VisitValidationStatus]:
    headers = [header.lower() for header in dataset.headers or []]
    if not headers:
        raise ImportException("The uploaded file did not contain any headers")

    visit_col_index = _get_header_index(headers, VISIT_ID_COL)
    status_col_index = _get_header_index(headers, STATUS_COL)
    reason_col_index = _get_header_index(headers, REASON_COL)
    status_by_visit_id = {}
    reason_by_visit_id = {}
    invalid_rows = []
    for row in dataset:
        row = list(row)
        visit_id = str(row[visit_col_index])
        status_raw = row[status_col_index].lower().strip().replace(" ", "_")
        try:
            status_by_visit_id[visit_id] = VisitValidationStatus[status_raw]
        except KeyError:
            invalid_rows.append((row, f"status must be one of {VisitValidationStatus.values}"))
        if status_raw == VisitValidationStatus.rejected.value:
            reason_by_visit_id[visit_id] = str(row[reason_col_index])

    if invalid_rows:
        raise ImportException(f"{len(invalid_rows)} have errors", invalid_rows)
    return status_by_visit_id, reason_by_visit_id


def get_imported_dataset(file, file_format):
    if file_format == "csv":
        file = codecs.iterdecode(file, "utf-8")
    imported_data = Dataset().load(file, format=file_format)
    return imported_data


def _get_header_index(headers: list[str], col_name: str) -> int:
    try:
        return headers.index(col_name)
    except ValueError:
        raise ImportException(f"Missing required column(s): '{col_name}'")


def bulk_update_payment_status(opportunity: Opportunity, file: UploadedFile) -> PaymentImportStatus:
    file_format = None
    if file.content_type:
        file_format = mimetypes.guess_extension(file.content_type)
        if file_format:
            file_format = file_format[1:]
    if not file_format:
        file_format = file.name.split(".")[-1].lower()
    if file_format not in ("csv", "xlsx"):
        raise ImportException(f"Invalid file format. Only 'CSV' and 'XLSX' are supported. Got {file_format}")
    imported_data = get_imported_dataset(file, file_format)
    return _bulk_update_payments(opportunity, imported_data)


def _bulk_update_payments(opportunity: Opportunity, imported_data: Dataset) -> PaymentImportStatus:
    headers = [header.lower() for header in imported_data.headers or []]
    if not headers:
        raise ImportException("The uploaded file did not contain any headers")

    username_col_index = _get_header_index(headers, USERNAME_COL)
    amount_col_index = _get_header_index(headers, AMOUNT_COL)
    invalid_rows = []
    payments = {}
    for row in imported_data:
        row = list(row)
        username = str(row[username_col_index])
        amount_raw = row[amount_col_index]
        if amount_raw:
            if not username:
                invalid_rows.append((row, "username required"))
            try:
                amount = int(amount_raw)
            except ValueError:
                invalid_rows.append((row, "amount must be an integer"))
            payments[username] = amount

    if invalid_rows:
        raise ImportException(f"{len(invalid_rows)} have errors", invalid_rows)

    seen_users = set()
    payment_ids = []
    with transaction.atomic():
        usernames = list(payments)
        users = OpportunityAccess.objects.filter(
            user__username__in=usernames, opportunity=opportunity, suspended=False
        ).select_related("user")
        for access in users:
            username = access.user.username
            amount = payments[username]
            payment = Payment.objects.create(opportunity_access=access, amount=amount)
            seen_users.add(username)
            payment_ids.append(payment.pk)
    missing_users = set(usernames) - seen_users
    send_payment_notification.delay(opportunity.id, payment_ids)
    return PaymentImportStatus(seen_users, missing_users)


def bulk_update_completed_work_status(opportunity: Opportunity, file: UploadedFile) -> CompletedWorkImportStatus:
    file_format = None
    if file.content_type:
        file_format = mimetypes.guess_extension(file.content_type)
        if file_format:
            file_format = file_format[1:]
    if not file_format:
        file_format = file.name.split(".")[-1].lower()
    if file_format not in ("csv", "xlsx"):
        raise ImportException(f"Invalid file format. Only 'CSV' and 'XLSX' are supported. Got {file_format}")
    imported_data = get_imported_dataset(file, file_format)
    return _bulk_update_completed_work_status(opportunity, imported_data)


def _bulk_update_completed_work_status(opportunity: Opportunity, dataset: Dataset):
    status_by_work_id, reasons_by_work_id = get_status_by_completed_work_id(dataset)
    work_ids = list(status_by_work_id)
    missing_completed_works = set()
    seen_completed_works = set()
    user_ids = set()
    with transaction.atomic():
        for work_batch in batched(work_ids, 100):
            to_update = []
            completed_works = CompletedWork.objects.filter(
                id__in=work_batch, opportunity_access__opportunity=opportunity
            )
            for completed_work in completed_works:
                seen_completed_works.add(str(completed_work.id))
                status = status_by_work_id[str(completed_work.id)]
                if completed_work.status != status:
                    completed_work.status = status
                    reason = reasons_by_work_id.get(str(completed_work.id))
                    if completed_work.status == CompletedWorkStatus.rejected and reason:
                        completed_work.reason = reason
                    to_update.append(completed_work)
                user_ids.add(completed_work.opportunity_access.user_id)
            CompletedWork.objects.bulk_update(to_update, fields=["status", "reason"])
            missing_completed_works |= set(work_batch) - seen_completed_works
        update_payment_accrued(opportunity, users=user_ids)
    return CompletedWorkImportStatus(seen_completed_works, missing_completed_works)


def get_status_by_completed_work_id(dataset):
    headers = [header.lower() for header in dataset.headers or []]
    if not headers:
        raise ImportException("The uploaded file did not contain any headers")

    work_id_col_index = _get_header_index(headers, WORK_ID_COL)
    status_col_index = _get_header_index(headers, PAYMENT_APPROVAL_STATUS_COL)
    reason_col_index = _get_header_index(headers, REASON_COL)
    status_by_work_id = {}
    reason_by_work_id = {}
    invalid_rows = []
    for row in dataset:
        row = list(row)
        work_id = str(row[work_id_col_index])
        status_raw = row[status_col_index].lower().strip().replace(" ", "_")
        try:
            status_by_work_id[work_id] = CompletedWorkStatus[status_raw]
        except KeyError:
            invalid_rows.append((row, f"status must be one of {CompletedWorkStatus.values}"))
        if status_raw == CompletedWorkStatus.rejected.value:
            reason_by_work_id[work_id] = str(row[reason_col_index])

    if invalid_rows:
        raise ImportException(f"{len(invalid_rows)} have errors", invalid_rows)
    return status_by_work_id, reason_by_work_id


def bulk_update_catchments(opportunity: Opportunity, file: UploadedFile):
    file_format = get_file_extension(file)
    if file_format not in ("csv", "xlsx"):
        raise ImportException(f"Invalid file format. Only 'CSV' and 'XLSX' are supported. Got {file_format}")
    imported_data = get_imported_dataset(file, file_format)
    _bulk_update_catchments(opportunity, imported_data)


def _bulk_update_catchments(opportunity: Opportunity, dataset: Dataset):
    headers = [header.lower() for header in dataset.headers or []]
    if not headers:
        raise ImportException("The uploaded file did not contain any headers")

    latitude_index = _get_header_index(headers, LATITUDE_COL)
    longitude_index = _get_header_index(headers, LONGITUDE_COL)
    active_index = _get_header_index(headers, ACTIVE_COL)
    radius_index = _get_header_index(headers, RADIUS_COL)
    area_name_index = _get_header_index(headers, AREA_NAME_COL)

    with transaction.atomic():
        to_create = []
        to_update = []

        opportunity_accesses = {}
        username_index = None
        if USERNAME_COL in headers:
            username_index = _get_header_index(headers, USERNAME_COL)
            opportunity_accesses = {
                oa.user.username: oa
                for oa in OpportunityAccess.objects.filter(opportunity=opportunity).select_related("user")
            }

        invalid_rows = []
        seen_catchments = set()
        missing_catchments = set()
        for row in dataset:
            row = list(row)  # Convert row iterator to list for indexing
            try:
                latitude = Decimal(row[latitude_index])
                longitude = Decimal(row[longitude_index])
                radius = int(row[radius_index])
                active = row[active_index].lower().strip() == "yes"
                area_name = str(row[area_name_index])

                if latitude < Decimal("-90") or latitude > Decimal("90"):
                    raise ValueError("Latitude must be between -90 and 90 degrees")

                if longitude < Decimal("-180") or longitude > Decimal("180"):
                    raise ValueError("Longitude must be between -180 and 180 degrees")

                if not radius:
                    raise ValueError("Radius must be an integer")

                if active_index is None or row[active_index].lower().strip() not in ["yes", "no"]:
                    raise ValueError("Active status must be 'yes' or 'no'")

                if area_name_index is None or not isinstance(row[area_name_index], str):
                    raise ValueError("Area name is not valid.")

                if not username_index or not row[username_index]:
                    catchment = CatchmentArea(
                        latitude=latitude,
                        longitude=longitude,
                        radius=radius,
                        opportunity=opportunity,
                        name=area_name,
                        active=active,
                    )
                    seen_catchments.add(catchment.name)
                    to_create.append(catchment)
                elif row[username_index] in opportunity_accesses:
                    username = row[username_index]
                    catchment = None
                    created = None
                    if CATCHMENT_ID in headers and row[_get_header_index(headers, CATCHMENT_ID)]:
                        catchment_id = row[_get_header_index(headers, CATCHMENT_ID)]
                        catchment, created = CatchmentArea.objects.get_or_create(
                            id=catchment_id,
                            defaults={
                                "latitude": latitude,
                                "longitude": longitude,
                                "radius": radius,
                                "opportunity_accesses": opportunity_accesses[username],
                                "opportunity": opportunity,
                                "name": area_name,
                                "active": active,
                            },
                        )

                    if not created:
                        catchment.latitude = latitude
                        catchment.longitude = longitude
                        catchment.radius = radius
                        catchment.active = active
                        catchment.opportunity_accesses = opportunity_accesses[username]
                        catchment.opportunity = opportunity
                        catchment.name = area_name
                        to_update.append(catchment)

                    seen_catchments.add(catchment.name)
                else:
                    missing_catchments.add(row[area_name_index])
                    invalid_rows.append((row, f"Invalid username {row[username_index]}"))

            except (ValueError, TypeError) as e:
                missing_catchments.add(row[area_name_index])
                invalid_rows.append((row, f"Invalid value type in row {row}: {e}"))

        if to_create:
            CatchmentArea.objects.bulk_create(to_create)

        if to_update:
            CatchmentArea.objects.bulk_update(to_update, ["latitude", "longitude", "radius", "active", "name"])

        if invalid_rows:
            raise ImportException(f"{len(invalid_rows)} have errors", invalid_rows)
    return CatchmentAreaImportStatus(seen_catchments, missing_catchments)
