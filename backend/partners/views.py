from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from gallery.serializers import PublicGalleryStorySerializer
from gallery.views import PublicGalleryStoriesView
from .models import Partner
from .serializers import PublicPartnerSerializer


class PublicPartnerListView(ListAPIView):
    serializer_class = PublicPartnerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Keep the approval restriction as the base queryset for every public search.
        queryset = Partner.objects.filter(
            gallery_status=Partner.ApprovalStatus.APPROVED
        )
        params = self.request.query_params
        search = params.get("q", "").strip()[:100]
        category = params.get("category", "").strip()
        city = params.get("city", "").strip()[:100]
        province = params.get("province", "").strip()[:100]
        country = params.get("country", "").strip()[:100]

        valid_categories = {value for value, _label in Partner.Category.choices}
        if category in valid_categories:
            queryset = queryset.filter(category=category)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if province:
            queryset = queryset.filter(province__icontains=province)
        if country:
            queryset = queryset.filter(country__icontains=country)
        if params.get("enquiry_ready") == "true":
            queryset = queryset.filter(enquiry_status=Partner.ApprovalStatus.APPROVED)
        if params.get("booking_ready") == "true":
            queryset = queryset.filter(booking_status=Partner.ApprovalStatus.APPROVED)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(city__icontains=search)
                | Q(province__icontains=search)
            )
        return queryset.order_by("name")


class PublicPartnerDetailView(APIView):
    """Public profile with only Gallery-published stories and approved profile fields."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        partner = get_object_or_404(
            Partner.objects.filter(gallery_status=Partner.ApprovalStatus.APPROVED),
            slug=slug,
        )
        published_stories = PublicGalleryStoriesView().get_queryset().filter(
            media__partner=partner
        )
        return Response({
            **PublicPartnerSerializer(partner, context={"request": request}).data,
            "stories": PublicGalleryStorySerializer(
                published_stories, many=True, context={"request": request}
            ).data,
        })


from rest_framework.generics import RetrieveAPIView
from .models import DestinationPage, ExperienceCollection
from .serializers import PublicDestinationSerializer, PublicExperienceCollectionSerializer


class PublicDestinationListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicDestinationSerializer

    def get_queryset(self):
        return DestinationPage.objects.filter(is_published=True).prefetch_related(
            "partners", "collections"
        ).order_by("display_order", "name")


class PublicDestinationDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicDestinationSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return DestinationPage.objects.filter(is_published=True).prefetch_related(
            "partners", "collections"
        )


class PublicExperienceCollectionListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicExperienceCollectionSerializer

    def get_queryset(self):
        queryset = ExperienceCollection.objects.filter(is_published=True).filter(
            Q(destination__isnull=True) | Q(destination__is_published=True)
        ).select_related(
            "destination"
        ).prefetch_related("partners")
        destination = self.request.query_params.get("destination", "").strip()[:180]
        if destination:
            queryset = queryset.filter(destination__slug=destination, destination__is_published=True)
        return queryset.order_by("display_order", "title")


class PublicExperienceCollectionDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicExperienceCollectionSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return ExperienceCollection.objects.filter(is_published=True).filter(
            Q(destination__isnull=True) | Q(destination__is_published=True)
        ).select_related(
            "destination"
        ).prefetch_related("partners")


from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from .models import PartnerEnquiry, TripPlan, TripPlanItem
from .serializers import (
    PartnerEnquiryCreateSerializer, PartnerEnquiryResponseSerializer,
    PartnerEnquirySerializer, TripPlanItemCreateSerializer, TripPlanSerializer,
)


class TripPlanListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = TripPlan.objects.filter(owner=request.user).prefetch_related(
            "items__partner"
        )
        return Response(TripPlanSerializer(plans, many=True).data)

    def post(self, request):
        serializer = TripPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save(owner=request.user)
        return Response(TripPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class TripPlanDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return TripPlan.objects.prefetch_related("items__partner").get(pk=pk, owner=request.user)
        except TripPlan.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Trip plan not found.")

    def get(self, request, pk):
        return Response(TripPlanSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk):
        plan = self.get_object(request, pk)
        serializer = TripPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TripPlanSerializer(plan).data)

    def delete(self, request, pk):
        self.get_object(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TripPlanItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            plan = TripPlan.objects.get(pk=pk, owner=request.user)
        except TripPlan.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Trip plan not found.")
        serializer = TripPlanItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        partner = Partner.objects.get(pk=serializer.validated_data["partner_id"])
        item, created = TripPlanItem.objects.get_or_create(
            plan=plan, partner=partner,
            defaults={"note": serializer.validated_data.get("note", "")},
        )
        if not created:
            raise ValidationError({"partner_id": "This partner is already in the trip plan."})
        plan.save(update_fields=["updated_at"])
        return Response(TripPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class TripPlanItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, item_id):
        try:
            item = TripPlanItem.objects.get(pk=item_id, plan__pk=pk, plan__owner=request.user)
        except TripPlanItem.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Trip plan item not found.")
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerEnquiryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enquiries = PartnerEnquiry.objects.filter(customer=request.user).select_related("partner")
        return Response(PartnerEnquirySerializer(enquiries, many=True).data)

    def post(self, request):
        serializer = PartnerEnquiryCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        enquiry = PartnerEnquiry.objects.create(
            customer=request.user,
            partner=data["partner"],
            trip_plan=data.get("trip_plan"),
            message=data["message"],
            requested_start_date=data.get("requested_start_date"),
            requested_end_date=data.get("requested_end_date"),
        )
        return Response(PartnerEnquirySerializer(enquiry).data, status=status.HTTP_201_CREATED)


class PartnerIncomingEnquiryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enquiries = PartnerEnquiry.objects.filter(
            partner__owner=request.user
        ).select_related("partner", "customer", "trip_plan")
        return Response(PartnerEnquirySerializer(enquiries, many=True).data)


class PartnerEnquiryRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            enquiry = PartnerEnquiry.objects.select_related("partner", "customer").get(
                pk=pk, partner__owner=request.user
            )
        except PartnerEnquiry.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Enquiry not found.")
        if enquiry.status != PartnerEnquiry.Status.PENDING:
            raise ValidationError("Only pending enquiries can receive a partner response.")
        serializer = PartnerEnquiryResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry.status = serializer.validated_data["status"]
        enquiry.partner_response = serializer.validated_data["partner_response"]
        enquiry.responded_at = timezone.now()
        enquiry.save(update_fields=["status", "partner_response", "responded_at", "updated_at"])
        return Response(PartnerEnquirySerializer(enquiry).data)

import uuid
import hashlib
import json
from urllib.parse import parse_qsl
from datetime import timedelta
from django.db import transaction
from .models import PartnerAvailability, ReservationRequest
from .serializers import (
    PartnerAvailabilitySerializer, ReservationDecisionSerializer,
    ReservationRequestCreateSerializer, ReservationRequestSerializer,
)


class PublicPartnerAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        partner_id = request.query_params.get("partner_id")
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        if not partner_id or not start or not end:
            raise ValidationError("partner_id, start_date and end_date are required.")
        partner = get_object_or_404(
            Partner, pk=partner_id,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        from django.utils.dateparse import parse_date
        start_date, end_date = parse_date(start), parse_date(end)
        if not start_date or not end_date or end_date <= start_date or (end_date - start_date).days > 90:
            raise ValidationError("Provide a valid date range of up to 90 nights.")
        days = PartnerAvailability.objects.filter(
            partner=partner, date__gte=start_date, date__lt=end_date, is_open=True
        ).order_by("date")
        return Response([{
            "date": day.date,
            "available_guests": max(0, day.capacity - day.booked_count),
            "price_per_guest": day.price_per_guest,
            "currency": day.currency,
        } for day in days])


class PartnerAvailabilityManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = PartnerAvailability.objects.filter(partner__owner=request.user).select_related("partner")
        partner_id = request.query_params.get("partner_id")
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        return Response(PartnerAvailabilitySerializer(queryset, many=True).data)

    def post(self, request):
        data = request.data.copy()
        partner_id = data.pop("partner_id", None)
        if not partner_id:
            raise ValidationError({"partner_id": "A partner profile is required."})
        partner = get_object_or_404(
            Partner, pk=partner_id, owner=request.user,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        from django.utils.dateparse import parse_date
        day_date = parse_date(str(data.get("date", "")))
        if not day_date:
            raise ValidationError({"date": "Provide a valid date."})
        with transaction.atomic():
            day = PartnerAvailability.objects.select_for_update().filter(partner=partner, date=day_date).first()
            serializer = PartnerAvailabilitySerializer(day, data=data)
            serializer.is_valid(raise_exception=True)
            saved = serializer.save(partner=partner)
        return Response(PartnerAvailabilitySerializer(saved).data, status=status.HTTP_200_OK if day else status.HTTP_201_CREATED)


class CustomerReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = ReservationRequest.objects.filter(customer=request.user).select_related("partner")
        return Response(ReservationRequestSerializer(items, many=True).data)

    def post(self, request):
        serializer = ReservationRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        item = ReservationRequest.objects.create(
            customer=request.user, partner=data["partner"], trip_plan=data.get("trip_plan"),
            start_date=data["start_date"], end_date=data["end_date"],
            guests=data["guests"], message=data.get("message", ""),
        )
        return Response(ReservationRequestSerializer(item).data, status=status.HTTP_201_CREATED)


class PartnerReservationInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = ReservationRequest.objects.filter(partner__owner=request.user).select_related("partner", "customer")
        return Response(ReservationRequestSerializer(items, many=True).data)


class PartnerReservationDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = ReservationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            try:
                item = ReservationRequest.objects.select_for_update().select_related("partner", "customer").get(
                    pk=pk, partner__owner=request.user
                )
            except ReservationRequest.DoesNotExist:
                from rest_framework.exceptions import NotFound
                raise NotFound("Reservation request not found.")
            if item.status != ReservationRequest.Status.PENDING:
                raise ValidationError("Only pending reservation requests can be decided.")
            decision = serializer.validated_data["status"]
            if decision == ReservationRequest.Status.CONFIRMED:
                if item.partner.booking_status != Partner.ApprovalStatus.APPROVED:
                    raise ValidationError("This partner is not currently approved to confirm bookings.")
                dates = [item.start_date + timedelta(days=offset) for offset in range((item.end_date - item.start_date).days)]
                days = list(PartnerAvailability.objects.select_for_update().filter(
                    partner=item.partner, date__in=dates
                ).order_by("date"))
                if len(days) != len(dates) or any(not day.is_open or day.capacity - day.booked_count < item.guests for day in days):
                    raise ValidationError("Availability or capacity has changed. The request cannot be confirmed.")
                for day in days:
                    day.booked_count += item.guests
                    day.save(update_fields=["booked_count", "updated_at"])
                item.booking_reference = uuid.uuid4()
            item.status = decision
            item.partner_response = serializer.validated_data["partner_response"]
            item.responded_at = timezone.now()
            item.save(update_fields=["status", "booking_reference", "partner_response", "responded_at", "updated_at"])
        return Response(ReservationRequestSerializer(item).data)


class CustomerReservationCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            try:
                item = ReservationRequest.objects.select_for_update().get(pk=pk, customer=request.user)
            except ReservationRequest.DoesNotExist:
                from rest_framework.exceptions import NotFound
                raise NotFound("Reservation request not found.")
            if item.status not in (ReservationRequest.Status.PENDING, ReservationRequest.Status.CONFIRMED):
                raise ValidationError("This reservation can no longer be cancelled.")
            if item.payments.filter(status=ReservationPayment.Status.CAPTURED).exists():
                raise ValidationError("This reservation has a captured payment. A refund workflow is required before cancellation.")
            if item.status == ReservationRequest.Status.CONFIRMED:
                dates = [item.start_date + timedelta(days=offset) for offset in range((item.end_date - item.start_date).days)]
                days = list(PartnerAvailability.objects.select_for_update().filter(
                    partner=item.partner, date__in=dates
                ).order_by("date"))
                for day in days:
                    day.booked_count = max(0, day.booked_count - item.guests)
                    day.save(update_fields=["booked_count", "updated_at"])
            item.status = ReservationRequest.Status.CANCELLED
            item.save(update_fields=["status", "updated_at"])
        return Response(ReservationRequestSerializer(item).data)

class PartnerBookingProfileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = Partner.objects.filter(
            owner=request.user, booking_status=Partner.ApprovalStatus.APPROVED
        ).order_by("name")
        return Response(PublicPartnerSerializer(profiles, many=True).data)
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from rest_framework.permissions import IsAdminUser
from .models import PartnerFinancialSettings, ReservationPayment, PartnerCommissionLedger, ReservationRefund, PartnerCommissionAdjustment, PaymentProviderEvent
from .gateways import (
    GatewayError, build_payfast_checkout, create_yoco_checkout,
    verify_payfast_signature, verify_payfast_source_ip, validate_payfast_itn,
    verify_yoco_webhook, create_payfast_refund, create_yoco_refund,
    query_payfast_refund,
)
from .serializers import (
    PartnerFinancialSettingsSerializer, ReservationPaymentCreateSerializer,
    ReservationPaymentSerializer, PaymentReconciliationSerializer,
    PartnerCommissionLedgerSerializer,
)


def _reservation_financial_totals(reservation):
    if reservation.quoted_total is not None:
        total = reservation.quoted_total
        currency = reservation.quoted_currency
        deposit = reservation.quoted_deposit or Decimal("0.00")
    else:
        dates = [
            reservation.start_date + timedelta(days=offset)
            for offset in range((reservation.end_date - reservation.start_date).days)
        ]
        days = list(PartnerAvailability.objects.filter(
            partner=reservation.partner, date__in=dates
        ).order_by("date"))
        if len(days) != len(dates) or any(day.price_per_guest is None for day in days):
            raise ValidationError("The partner has not published a complete price for every reserved night.")
        currencies = {day.currency for day in days}
        if len(currencies) != 1:
            raise ValidationError("The reservation contains inconsistent pricing currencies.")
        currency = currencies.pop()
        total = sum((day.price_per_guest * reservation.guests for day in days), Decimal("0.00"))
        policy, _created = PartnerFinancialSettings.objects.get_or_create(partner=reservation.partner)
        if policy.currency != currency:
            raise ValidationError("The partner financial currency does not match the published availability currency.")
        if policy.deposit_type == PartnerFinancialSettings.DepositType.PERCENTAGE:
            deposit = (total * policy.deposit_value / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif policy.deposit_type == PartnerFinancialSettings.DepositType.FIXED:
            deposit = min(total, policy.deposit_value)
        else:
            deposit = Decimal("0.00")
        reservation.quoted_total = total
        reservation.quoted_deposit = deposit
        reservation.quoted_currency = currency
        reservation.quoted_at = timezone.now()
        reservation.save(update_fields=["quoted_total", "quoted_deposit", "quoted_currency", "quoted_at", "updated_at"])
    captured_payments = reservation.payments.filter(status=ReservationPayment.Status.CAPTURED)
    captured_total = captured_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    refunded_total = ReservationRefund.objects.filter(
        payment__in=captured_payments, status=ReservationRefund.Status.REFUNDED
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    paid = captured_total - refunded_total
    pending = reservation.payments.filter(status=ReservationPayment.Status.PENDING).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")
    return total, currency, deposit, paid, pending


class PartnerFinancialSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        partner_id = request.query_params.get("partner_id")
        queryset = PartnerFinancialSettings.objects.filter(partner__owner=request.user)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        return Response(PartnerFinancialSettingsSerializer(queryset, many=True).data)

    def post(self, request):
        data = request.data.copy()
        partner_id = data.pop("partner_id", None)
        partner = get_object_or_404(Partner, pk=partner_id, owner=request.user, booking_status=Partner.ApprovalStatus.APPROVED)
        with transaction.atomic():
            settings_obj, _created = PartnerFinancialSettings.objects.select_for_update().get_or_create(partner=partner)
            requested_currency = str(data.get("currency", settings_obj.currency)).upper()
            if requested_currency != settings_obj.currency and (
                ReservationPayment.objects.filter(partner=partner).exists()
                or PartnerAvailability.objects.filter(partner=partner).exclude(currency=requested_currency).exists()
            ):
                raise ValidationError("Currency can only change before payments exist and when all published availability uses the new currency.")
            serializer = PartnerFinancialSettingsSerializer(settings_obj, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            saved = serializer.save()
        return Response(PartnerFinancialSettingsSerializer(saved).data)


class ReservationPaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = ReservationPayment.objects.filter(customer=request.user).select_related("partner", "reservation")
        return Response(ReservationPaymentSerializer(payments, many=True).data)

    def post(self, request):
        serializer = ReservationPaymentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reservation = serializer.validated_data["reservation"]
        key = serializer.validated_data["idempotency_key"]
        with transaction.atomic():
            reservation = ReservationRequest.objects.select_for_update().get(pk=reservation.pk, customer=request.user)
            if reservation.status != ReservationRequest.Status.CONFIRMED:
                raise ValidationError("Only confirmed reservations can be paid.")
            existing = ReservationPayment.objects.filter(customer=request.user, idempotency_key=key).first()
            if existing:
                if existing.reservation_id != reservation.pk:
                    raise ValidationError("This idempotency key has already been used for another reservation.")
                return Response(ReservationPaymentSerializer(existing).data)
            total, currency, deposit, paid, pending = _reservation_financial_totals(reservation)
            remaining = max(Decimal("0.00"), total - paid)
            if remaining <= 0:
                raise ValidationError("This reservation has already been paid in full.")
            if pending > 0:
                raise ValidationError("A payment is already awaiting reconciliation for this reservation.")
            deposit_due = max(Decimal("0.00"), deposit - paid)
            if deposit_due > 0:
                amount, kind = min(deposit_due, remaining), ReservationPayment.Kind.DEPOSIT
            else:
                amount, kind = remaining, ReservationPayment.Kind.BALANCE
            payment = ReservationPayment.objects.create(
                reservation=reservation, customer=request.user, partner=reservation.partner,
                kind=kind, amount=amount, currency=currency, idempotency_key=key,
            )
        return Response(ReservationPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class AdminPaymentReconciliationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = PaymentReconciliationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            try:
                reservation_id = ReservationPayment.objects.only("reservation_id").get(pk=pk).reservation_id
                locked_reservation = ReservationRequest.objects.select_for_update().get(pk=reservation_id)
                payment = ReservationPayment.objects.select_for_update().select_related("partner").get(pk=pk)
                payment.reservation = locked_reservation
            except (ReservationPayment.DoesNotExist, ReservationRequest.DoesNotExist):
                from rest_framework.exceptions import NotFound
                raise NotFound("Payment record not found.")
            if payment.status != ReservationPayment.Status.PENDING:
                if payment.status == data["status"] and payment.provider_reference == (data.get("provider_reference") or None):
                    return Response(ReservationPaymentSerializer(payment).data)
                raise ValidationError("Only pending payment records can be reconciled.")
            if data["status"] == ReservationPayment.Status.CAPTURED and payment.reservation.status != ReservationRequest.Status.CONFIRMED:
                raise ValidationError("A payment cannot be captured for a cancelled or unconfirmed reservation.")
            payment.provider = data["provider"]
            payment.provider_reference = data.get("provider_reference") or None
            payment.failure_reason = data.get("failure_reason", "")
            payment.status = data["status"]
            if payment.status == ReservationPayment.Status.CAPTURED:
                payment.captured_at = timezone.now()
            payment.save(update_fields=["provider", "provider_reference", "failure_reason", "status", "captured_at", "updated_at"])
            if payment.status == ReservationPayment.Status.CAPTURED:
                policy, _created = PartnerFinancialSettings.objects.get_or_create(partner=payment.partner)
                rate = policy.commission_rate
                commission = (payment.amount * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                PartnerCommissionLedger.objects.get_or_create(
                    payment=payment,
                    defaults={
                        "partner": payment.partner,
                        "gross_amount": payment.amount,
                        "commission_rate": rate,
                        "commission_amount": commission,
                        "partner_net_amount": payment.amount - commission,
                    },
                )
        return Response(ReservationPaymentSerializer(payment).data)


class PartnerFinancialSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        partner_id = request.query_params.get("partner_id")
        partner = get_object_or_404(Partner, pk=partner_id, owner=request.user)
        captured_payments = ReservationPayment.objects.filter(
            partner=partner, status=ReservationPayment.Status.CAPTURED
        )
        captured_gross = captured_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        refunded = ReservationRefund.objects.filter(
            payment__in=captured_payments, status=ReservationRefund.Status.REFUNDED
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        captured = captured_gross - refunded
        entries = PartnerCommissionLedger.objects.filter(partner=partner).select_related("payment")
        accrued_gross = entries.filter(status=PartnerCommissionLedger.Status.ACCRUED).aggregate(
            total=Sum("commission_amount")
        )["total"] or Decimal("0.00")
        net_gross = entries.exclude(status=PartnerCommissionLedger.Status.VOID).aggregate(
            total=Sum("partner_net_amount")
        )["total"] or Decimal("0.00")
        adjustments = PartnerCommissionAdjustment.objects.filter(partner=partner)
        commission_reversed = adjustments.aggregate(total=Sum("commission_reversal"))["total"] or Decimal("0.00")
        partner_net_reversed = adjustments.aggregate(total=Sum("partner_net_reversal"))["total"] or Decimal("0.00")
        accrued = accrued_gross - commission_reversed
        net = net_gross - partner_net_reversed
        return Response({
            "partner_id": partner.pk,
            "currency": partner.financial_settings.currency if hasattr(partner, "financial_settings") else "ZAR",
            "captured_payments_total": captured,
            "accrued_commission_total": accrued,
            "partner_net_total": net,
            "commission_entries": PartnerCommissionLedgerSerializer(entries, many=True).data,
            "payouts_enabled": False,
        })




def _finalize_provider_refund(refund, provider_reference="", reconciled_by=None):
    from .models import ReservationRefund, PartnerCommissionAdjustment
    with transaction.atomic():
        refund = ReservationRefund.objects.select_for_update().select_related("payment", "payment__partner").get(pk=refund.pk)
        payment = ReservationPayment.objects.select_for_update().select_related("partner").get(pk=refund.payment_id)
        if refund.status == ReservationRefund.Status.REFUNDED:
            return refund
        if refund.status != ReservationRefund.Status.PENDING:
            return refund
        refunded_total = ReservationRefund.objects.filter(
            payment=payment, status=ReservationRefund.Status.REFUNDED
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        if refund.amount > payment.amount - refunded_total:
            raise ValidationError("Provider-confirmed refund would exceed the remaining captured amount.")
        try:
            commission_entry = payment.commission_entry
        except PartnerCommissionLedger.DoesNotExist:
            raise ValidationError("The captured payment has no commission ledger entry.")
        prior_reversal = PartnerCommissionAdjustment.objects.filter(
            refund__payment=payment
        ).aggregate(total=Sum("commission_reversal"))["total"] or Decimal("0.00")
        target_reversal = (
            commission_entry.commission_amount * (refunded_total + refund.amount) / payment.amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        commission_reversal = min(
            commission_entry.commission_amount - prior_reversal,
            max(Decimal("0.00"), target_reversal - prior_reversal),
        )
        refund.status = ReservationRefund.Status.REFUNDED
        refund.provider_reference = provider_reference or refund.provider_reference
        refund.provider_status = "succeeded"
        refund.reconciled_at = timezone.now()
        if reconciled_by:
            refund.reconciled_by = reconciled_by
        refund.save(update_fields=["status", "provider_reference", "provider_status", "reconciled_at", "reconciled_by"])
        PartnerCommissionAdjustment.objects.get_or_create(
            refund=refund,
            defaults={
                "partner": payment.partner,
                "gross_refund": refund.amount,
                "commission_reversal": commission_reversal,
                "partner_net_reversal": refund.amount - commission_reversal,
            },
        )
        if refunded_total + refund.amount == payment.amount:
            payment.status = ReservationPayment.Status.REFUNDED
            payment.save(update_fields=["status", "updated_at"])
        return refund


class AdminPaymentRefundInitiateView(APIView):
    """Staff-only gateway refund initiation; final status comes from provider evidence."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        from .models import ReservationRefund
        from .serializers import ReservationRefundSerializer
        key = str(request.data.get("idempotency_key", "")).strip()
        reason = str(request.data.get("reason", "")).strip()[:500]
        if not key or len(key) < 8 or len(key) > 100:
            raise ValidationError({"idempotency_key": "Provide an 8–100 character idempotency key."})
        try:
            amount = Decimal(str(request.data.get("amount"))).quantize(Decimal("0.01"))
        except Exception:
            raise ValidationError({"amount": "Provide a valid refund amount."})
        if amount <= 0:
            raise ValidationError({"amount": "Refund amount must be greater than zero."})
        with transaction.atomic():
            payment = get_object_or_404(
                ReservationPayment.objects.select_for_update().select_related("partner"), pk=pk
            )
            existing = ReservationRefund.objects.filter(idempotency_key=key).first()
            if existing:
                if existing.payment_id == payment.pk and existing.amount == amount:
                    return Response(ReservationRefundSerializer(existing).data)
                raise ValidationError("This idempotency key has already been used.")
            if payment.status != ReservationPayment.Status.CAPTURED or not payment.provider_reference:
                raise ValidationError("Only captured payments with a verified provider reference can be refunded.")
            if payment.provider not in {"payfast", "yoco"}:
                raise ValidationError("Automated refunds are available only for PayFast and Yoco payments.")
            if ReservationRefund.objects.filter(payment=payment, status=ReservationRefund.Status.PENDING).exists():
                raise ValidationError("A refund is already pending for this payment. Resolve it before starting another.")
            refunded = ReservationRefund.objects.filter(
                payment=payment, status=ReservationRefund.Status.REFUNDED
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            if amount > payment.amount - refunded:
                raise ValidationError({"amount": "Refund exceeds the remaining captured amount."})
            refund = ReservationRefund.objects.create(
                payment=payment, amount=amount, currency=payment.currency,
                status=ReservationRefund.Status.PENDING, provider=payment.provider,
                idempotency_key=key, reason=reason, provider_status="request_created",
            )
        try:
            result = create_payfast_refund(payment, refund) if payment.provider == "payfast" else create_yoco_refund(payment, refund)
        except (GatewayError, ImproperlyConfigured) as exc:
            refund.provider_status = "submission_uncertain"
            refund.save(update_fields=["provider_status"])
            return Response({
                "refund": ReservationRefundSerializer(refund).data,
                "detail": str(exc),
                "manual_verification_required": True,
            }, status=status.HTTP_202_ACCEPTED)
        refund.provider_reference = result.get("provider_reference") or None
        refund.provider_status = result.get("status", "pending")
        refund.save(update_fields=["provider_reference", "provider_status"])
        if payment.provider == "yoco" and result.get("status") == "succeeded":
            refund = _finalize_provider_refund(refund, result.get("provider_reference", ""))
        return Response(ReservationRefundSerializer(refund).data, status=status.HTTP_202_ACCEPTED)


class AdminPayFastRefundVerifyView(APIView):
    """Verify PayFast refundable balance before staff finalise pending refunds."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        from .models import ReservationRefund
        from .serializers import ReservationRefundSerializer
        payment = get_object_or_404(ReservationPayment, pk=pk, provider="payfast")
        try:
            provider_state = query_payfast_refund(payment)
        except (GatewayError, ImproperlyConfigured) as exc:
            raise ValidationError(str(exc))
        if provider_state.get("status") not in {"COMPLETED", "REFUNDABLE"}:
            raise ValidationError("PayFast has not reported a verifiable refund state.")
        pending = list(ReservationRefund.objects.filter(
            payment=payment, status=ReservationRefund.Status.PENDING
        ).order_by("created_at"))
        if not pending:
            return Response({"refunds": [], "provider_status": provider_state.get("status")})
        available = provider_state.get("amount_available_for_refund")
        original = provider_state.get("amount_original")
        if available is None or original is None:
            raise ValidationError("PayFast refund query did not return original and remaining amounts.")
        refunded_by_provider = Decimal(str(int(original) - int(available))) / Decimal("100")
        already_reconciled = ReservationRefund.objects.filter(
            payment=payment, status=ReservationRefund.Status.REFUNDED
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        capacity = refunded_by_provider - already_reconciled
        results = []
        for refund in pending:
            if capacity < refund.amount:
                break
            results.append(_finalize_provider_refund(refund, refund.provider_reference or ""))
            capacity -= refund.amount
        return Response({
            "refunds": ReservationRefundSerializer(results, many=True).data,
            "provider_status": provider_state.get("status"),
            "provider_refunded_total": refunded_by_provider,
        })


class AdminPaymentRefundView(APIView):
    """Staff reconcile an externally completed refund; this endpoint does not call a gateway."""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        from .models import ReservationRefund
        from .serializers import ReservationRefundSerializer
        payment = get_object_or_404(ReservationPayment, pk=pk)
        refunds = ReservationRefund.objects.filter(payment=payment)
        return Response(ReservationRefundSerializer(refunds, many=True).data)

    def post(self, request, pk):
        from decimal import ROUND_HALF_UP
        from .models import ReservationRefund, PartnerCommissionAdjustment
        from .serializers import RefundReconciliationSerializer, ReservationRefundSerializer

        serializer = RefundReconciliationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            try:
                reservation_id = ReservationPayment.objects.only("reservation_id").get(pk=pk).reservation_id
                reservation = ReservationRequest.objects.select_for_update().get(pk=reservation_id)
                payment = ReservationPayment.objects.select_for_update().select_related("partner").get(pk=pk)
            except (ReservationPayment.DoesNotExist, ReservationRequest.DoesNotExist):
                from rest_framework.exceptions import NotFound
                raise NotFound("Payment record not found.")

            if payment.status not in (ReservationPayment.Status.CAPTURED, ReservationPayment.Status.REFUNDED):
                raise ValidationError("Only captured payments can be refunded.")
            if not payment.provider_reference:
                raise ValidationError("The captured payment must have a verified provider reference.")

            duplicate = ReservationRefund.objects.filter(provider_reference=data["provider_reference"]).first()
            if duplicate:
                if duplicate.payment_id == payment.pk and duplicate.amount == data["amount"] and duplicate.status == ReservationRefund.Status.REFUNDED:
                    return Response(ReservationRefundSerializer(duplicate).data)
                raise ValidationError("This provider refund reference has already been used.")

            refunded_total = ReservationRefund.objects.filter(
                payment=payment, status=ReservationRefund.Status.REFUNDED
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            remaining = payment.amount - refunded_total
            amount = data["amount"]
            if amount > remaining:
                raise ValidationError({"amount": f"Refund exceeds the remaining refundable amount of {remaining} {payment.currency}."})

            refund = ReservationRefund.objects.create(
                payment=payment, amount=amount, currency=payment.currency,
                status=ReservationRefund.Status.REFUNDED, provider=data["provider"],
                provider_reference=data["provider_reference"], idempotency_key="manual:" + data["provider_reference"],
                provider_status="reconciled", reason=data.get("reason", ""),
                reconciled_by=request.user, reconciled_at=timezone.now(),
            )

            try:
                commission_entry = payment.commission_entry
            except PartnerCommissionLedger.DoesNotExist:
                raise ValidationError("The captured payment has no commission ledger entry; refund reconciliation was not completed.")

            prior_reversal = PartnerCommissionAdjustment.objects.filter(
                refund__payment=payment
            ).aggregate(total=Sum("commission_reversal"))["total"] or Decimal("0.00")
            target_reversal = (
                commission_entry.commission_amount * (refunded_total + amount) / payment.amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            commission_reversal = min(
                commission_entry.commission_amount - prior_reversal,
                max(Decimal("0.00"), target_reversal - prior_reversal),
            )
            PartnerCommissionAdjustment.objects.create(
                refund=refund, partner=payment.partner, gross_refund=amount,
                commission_reversal=commission_reversal,
                partner_net_reversal=amount - commission_reversal,
            )

            if refunded_total + amount == payment.amount:
                payment.status = ReservationPayment.Status.REFUNDED
                payment.save(update_fields=["status", "updated_at"])

        return Response(ReservationRefundSerializer(refund).data, status=status.HTTP_201_CREATED)


class ReservationCheckoutStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        provider = str(request.data.get("provider", "")).strip().lower()
        if provider not in {"payfast", "yoco"}:
            raise ValidationError({"provider": "Choose payfast or yoco."})
        with transaction.atomic():
            payment = get_object_or_404(
                ReservationPayment.objects.select_for_update().select_related("reservation"),
                pk=pk, customer=request.user,
            )
            if payment.status != ReservationPayment.Status.PENDING:
                raise ValidationError("Only pending payments can start checkout.")
            if payment.reservation.status != ReservationRequest.Status.CONFIRMED:
                raise ValidationError("Checkout is available only for confirmed reservations.")
            if payment.provider not in {"manual_reconciliation", provider}:
                raise ValidationError("This payment has already been assigned to another provider.")
            if payment.checkout_url and payment.checkout_session_id:
                if payment.provider == "payfast":
                    result = build_payfast_checkout(payment)
                else:
                    result = {
                        "checkout_url": payment.checkout_url,
                        "checkout_session_id": payment.checkout_session_id,
                        "form_fields": None,
                    }
            else:
                try:
                    result = (
                        build_payfast_checkout(payment)
                        if provider == "payfast" else create_yoco_checkout(payment)
                    )
                except (GatewayError, ImproperlyConfigured) as exc:
                    raise ValidationError(str(exc))
                payment.provider = provider
                payment.checkout_url = result["checkout_url"]
                payment.checkout_session_id = result["checkout_session_id"]
                payment.save(update_fields=["provider", "checkout_url", "checkout_session_id", "updated_at"])
        return Response({
            "payment": ReservationPaymentSerializer(payment).data,
            "provider": provider,
            "checkout_url": result["checkout_url"],
            "form_fields": result.get("form_fields"),
        })


class PaymentProviderWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = []

    def post(self, request, provider):
        provider = provider.lower()
        raw_body = request.body
        if provider == "yoco":
            verified, verification_result = verify_yoco_webhook(raw_body, request.headers)
            if not verified:
                return Response({"detail": verification_result}, status=status.HTTP_400_BAD_REQUEST)
            event_id = verification_result
            try:
                event = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return Response({"detail": "Invalid JSON webhook body."}, status=status.HTTP_400_BAD_REQUEST)
            if not isinstance(event, dict) or not isinstance(event.get("payload"), dict):
                return Response({"detail": "Invalid Yoco event structure."}, status=status.HTTP_400_BAD_REQUEST)
            event_type = event.get("type")
            payload = event["payload"]
            metadata = payload.get("metadata")
            checkout_id = metadata.get("checkoutId") if isinstance(metadata, dict) else None
            if event_type in {"refund.succeeded", "refund.failed"}:
                if not checkout_id:
                    return Response({"detail": "Yoco refund event has no checkout reference."}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    payment = ReservationPayment.objects.get(provider="yoco", checkout_session_id=str(checkout_id))
                except ReservationPayment.DoesNotExist:
                    return Response({"detail": "Yoco refund checkout is not recognised."}, status=status.HTTP_404_NOT_FOUND)
                if payload.get("currency") != payment.currency or not isinstance(payload.get("amount"), int):
                    return Response({"detail": "Yoco refund amount or currency is invalid."}, status=status.HTTP_400_BAD_REQUEST)
                refund_amount = (Decimal(payload["amount"]) / Decimal("100")).quantize(Decimal("0.01"))
                with transaction.atomic():
                    event_record, created = PaymentProviderEvent.objects.get_or_create(
                        provider="yoco", event_id=event_id,
                        defaults={"payload_sha256": hashlib.sha256(raw_body).hexdigest(), "signature_verified": True},
                    )
                    if not created:
                        return Response({"received": True, "duplicate": True}, status=status.HTTP_200_OK)
                    refund = ReservationRefund.objects.select_for_update().filter(
                        payment=payment, amount=refund_amount,
                        status=ReservationRefund.Status.PENDING,
                    ).order_by("created_at").first()
                    if not refund:
                        # A synchronous success response may already have finalised this refund.
                        refund = ReservationRefund.objects.filter(
                            payment=payment, amount=refund_amount,
                            status=ReservationRefund.Status.REFUNDED,
                        ).order_by("-reconciled_at").first()
                        if refund:
                            event_record.processed_at = timezone.now()
                            event_record.save(update_fields=["processed_at"])
                            return Response({"received": True, "already_reconciled": True}, status=status.HTTP_200_OK)
                        event_record.delete()
                        return Response({"detail": "No matching pending Yoco refund exists."}, status=status.HTTP_404_NOT_FOUND)
                    if event_type == "refund.succeeded":
                        refund = _finalize_provider_refund(refund, str(payload.get("id") or event_id))
                    else:
                        refund.status = ReservationRefund.Status.FAILED
                        refund.provider_status = str(payload.get("failureReason") or "failed")[:40]
                        refund.save(update_fields=["status", "provider_status"])
                    event_record.processed_at = timezone.now()
                    event_record.save(update_fields=["processed_at"])
                return Response({"received": True}, status=status.HTTP_200_OK)
            if event_type != "payment.succeeded":
                return Response({"received": True}, status=status.HTTP_200_OK)
            if not checkout_id:
                return Response({"detail": "Yoco payment event has no checkout reference."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                payment = ReservationPayment.objects.select_related("reservation", "partner").get(
                    provider="yoco", checkout_session_id=str(checkout_id)
                )
            except ReservationPayment.DoesNotExist:
                return Response({"detail": "Checkout session is not recognised."}, status=status.HTTP_404_NOT_FOUND)
            expected_cents = int((payment.amount * Decimal("100")).quantize(Decimal("1")))
            if payload.get("amount") != expected_cents or payload.get("currency") != payment.currency:
                return Response({"detail": "Yoco amount or currency does not match the reservation payment."}, status=status.HTTP_400_BAD_REQUEST)
            provider_reference = str(checkout_id)
            success = payload.get("status") == "succeeded"
            payload_hash = hashlib.sha256(raw_body).hexdigest()
        elif provider == "payfast":
            form_data = dict(parse_qsl(raw_body.decode("utf-8"), keep_blank_values=True))
            if not verify_payfast_signature(form_data):
                return Response({"detail": "Invalid PayFast ITN signature."}, status=status.HTTP_400_BAD_REQUEST)
            if not verify_payfast_source_ip(request.META.get("REMOTE_ADDR")):
                return Response({"detail": "PayFast source IP could not be verified."}, status=status.HTTP_403_FORBIDDEN)
            configured_merchant = str(getattr(settings, "PAYFAST_MERCHANT_ID", ""))
            if not configured_merchant or form_data.get("merchant_id") != configured_merchant:
                return Response({"detail": "PayFast merchant ID does not match."}, status=status.HTTP_400_BAD_REQUEST)
            if not validate_payfast_itn(raw_body):
                return Response({"detail": "PayFast server-side ITN validation failed."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                payment = ReservationPayment.objects.select_related("reservation", "partner").get(
                    pk=int(form_data.get("m_payment_id", "0")), provider="payfast"
                )
            except (ReservationPayment.DoesNotExist, TypeError, ValueError):
                return Response({"detail": "PayFast payment reference is not recognised."}, status=status.HTTP_404_NOT_FOUND)
            try:
                gross = Decimal(str(form_data.get("amount_gross", ""))).quantize(Decimal("0.01"))
            except Exception:
                return Response({"detail": "PayFast gross amount is invalid."}, status=status.HTTP_400_BAD_REQUEST)
            if gross != payment.amount or payment.currency != "ZAR":
                return Response({"detail": "PayFast amount or currency does not match the reservation payment."}, status=status.HTTP_400_BAD_REQUEST)
            event_status = str(form_data.get("payment_status", "")).upper()
            if event_status not in {"COMPLETE", "CANCELLED"}:
                return Response({"received": True}, status=status.HTTP_200_OK)
            provider_reference = str(form_data.get("pf_payment_id", "")).strip()
            if not provider_reference:
                return Response({"detail": "PayFast transaction reference is missing."}, status=status.HTTP_400_BAD_REQUEST)
            event_id = f"{provider_reference}:{event_status}"
            success = event_status == "COMPLETE"
            payload_hash = hashlib.sha256(raw_body).hexdigest()
        else:
            return Response({"detail": "Unsupported payment provider."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            try:
                reservation = ReservationRequest.objects.select_for_update().get(pk=payment.reservation_id)
                locked_payment = ReservationPayment.objects.select_for_update().get(pk=payment.pk)
            except (ReservationRequest.DoesNotExist, ReservationPayment.DoesNotExist):
                return Response({"detail": "Payment record no longer exists."}, status=status.HTTP_404_NOT_FOUND)
            event_record, created = PaymentProviderEvent.objects.get_or_create(
                provider=provider, event_id=event_id,
                defaults={"payload_sha256": payload_hash, "signature_verified": True},
            )
            if not created:
                return Response({"received": True, "duplicate": True}, status=status.HTTP_200_OK)
            if locked_payment.status == ReservationPayment.Status.PENDING:
                if success:
                    if reservation.status != ReservationRequest.Status.CONFIRMED:
                        event_record.delete()
                        return Response({"detail": "Cannot capture a payment for an unconfirmed reservation."}, status=status.HTTP_409_CONFLICT)
                    locked_payment.status = ReservationPayment.Status.CAPTURED
                    locked_payment.provider_reference = provider_reference
                    locked_payment.captured_at = timezone.now()
                    locked_payment.save(update_fields=["status", "provider_reference", "captured_at", "updated_at"])
                    policy, _created = PartnerFinancialSettings.objects.get_or_create(partner=locked_payment.partner)
                    commission = (locked_payment.amount * policy.commission_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    PartnerCommissionLedger.objects.get_or_create(
                        payment=locked_payment,
                        defaults={
                            "partner": locked_payment.partner,
                            "gross_amount": locked_payment.amount,
                            "commission_rate": policy.commission_rate,
                            "commission_amount": commission,
                            "partner_net_amount": locked_payment.amount - commission,
                        },
                    )
                else:
                    locked_payment.status = ReservationPayment.Status.FAILED
                    locked_payment.failure_reason = f"{provider.title()} reported payment failure."
                    locked_payment.save(update_fields=["status", "failure_reason", "updated_at"])
            elif success and locked_payment.status == ReservationPayment.Status.CAPTURED and locked_payment.provider_reference == provider_reference:
                pass
            else:
                event_record.delete()
                return Response({"detail": "Payment state conflicts with this provider event."}, status=status.HTTP_409_CONFLICT)
            event_record.processed_at = timezone.now()
            event_record.save(update_fields=["processed_at"])
        return Response({"received": True}, status=status.HTTP_200_OK)
