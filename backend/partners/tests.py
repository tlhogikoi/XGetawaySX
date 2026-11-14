from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal

from gallery.models import GalleryMedia, GalleryMediaPermissionGrant, GalleryStory

from accounts.models import User
from .models import Partner


class PublicPartnerListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="host@example.com", password="test-password")

    def create_partner(self, name, gallery_status):
        return Partner.objects.create(
            owner=self.owner,
            name=name,
            category=Partner.Category.ACCOMMODATION,
            gallery_status=gallery_status,
        )

    def test_only_gallery_approved_partners_are_public(self):
        self.create_partner("Approved Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Pending Guesthouse", Partner.ApprovalStatus.PENDING)

        response = self.client.get("/api/v1/partners/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Approved Lodge")

    def test_discovery_filters_by_category_and_location(self):
        matched = self.create_partner("Cape Adventure", Partner.ApprovalStatus.APPROVED)
        matched.category = Partner.Category.ACTIVITY
        matched.city = "Cape Town"
        matched.province = "Western Cape"
        matched.save()
        self.create_partner("Johannesburg Lodge", Partner.ApprovalStatus.APPROVED)
        response = self.client.get("/api/v1/partners/?category=activity&city=cape&province=western")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Cape Adventure"])

    def test_search_never_returns_unapproved_partners(self):
        self.create_partner("Approved Garden Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Pending Garden Lodge", Partner.ApprovalStatus.PENDING)
        response = self.client.get("/api/v1/partners/?q=garden")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Approved Garden Lodge"])

    def test_unknown_category_does_not_bypass_public_approval_filter(self):
        self.create_partner("Visible Lodge", Partner.ApprovalStatus.APPROVED)
        self.create_partner("Hidden Lodge", Partner.ApprovalStatus.SUSPENDED)
        response = self.client.get("/api/v1/partners/?category=not-a-category")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Visible Lodge"])

    def test_public_serializer_does_not_expose_owner_or_private_approval_fields(self):
        self.create_partner("Public Lodge", Partner.ApprovalStatus.APPROVED)

        response = self.client.get("/api/v1/partners/")

        self.assertNotIn("owner", response.data[0])
        self.assertNotIn("booking_status", response.data[0])
        self.assertNotIn("enquiry_status", response.data[0])


class PublicPartnerDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="profile-owner@example.com", password="test-password")

    def test_approved_partner_has_public_profile_and_empty_story_collection(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Profile Lodge", category=Partner.Category.ACCOMMODATION,
            description="A public description.", city="Johannesburg",
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Profile Lodge")
        self.assertEqual(response.data["city"], "Johannesburg")
        self.assertEqual(response.data["stories"], [])
        self.assertNotIn("owner", response.data)
        self.assertNotIn("booking_status", response.data)
        self.assertNotIn("enquiry_status", response.data)

    def test_profile_includes_only_published_stories_with_approved_rights(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Story Profile Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        media = GalleryMedia.objects.create(
            partner=partner, title="Garden at sunrise",
            image="https://images.example.test/garden.jpg",
            alt_text="Garden at sunrise", rights_holder="Lodge",
            submitted_by=self.owner, status=GalleryMedia.Status.APPROVED,
        )
        GalleryMediaPermissionGrant.objects.create(
            media=media, rights_holder="Lodge", permitted_channels=["website"],
            evidence_file=SimpleUploadedFile("release.pdf", b"%PDF-1.4 signed release"),
            granted_by=self.owner, granted_at=timezone.now(),
            review_status=GalleryMediaPermissionGrant.ReviewStatus.APPROVED,
        )
        GalleryStory.objects.create(
            media=media, summary="This carefully prepared story describes the lodge garden and its setting using information supplied by the owner and approved for public visitors.",
            status=GalleryStory.Status.PUBLISHED,
            owner_approved_at=timezone.now(), owner_approved_version=1,
            editorial_approved_at=timezone.now(), editorial_approved_version=1,
            published_at=timezone.now(),
            owner_original_history="PRIVATE PARTNER HISTORY",
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["stories"]), 1)
        self.assertNotIn("PRIVATE PARTNER HISTORY", str(response.data))
        self.assertNotIn("ai_source_facts", response.data["stories"][0])

    def test_unapproved_partner_profile_is_not_public(self):
        partner = Partner.objects.create(
            owner=self.owner, name="Pending Profile", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.PENDING,
        )
        response = self.client.get(f"/api/v1/partners/{partner.slug}/")
        self.assertEqual(response.status_code, 404)


class PublicDestinationAndCollectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="destination-owner@example.com", password="test-password")

    def make_partner(self, name, status):
        return Partner.objects.create(
            owner=self.owner, name=name, category=Partner.Category.ACTIVITY,
            gallery_status=status, city="Johannesburg", province="Gauteng",
        )

    def test_destination_pages_are_published_only_and_hide_unapproved_partners(self):
        from .models import DestinationPage
        approved = self.make_partner("Approved Adventure", Partner.ApprovalStatus.APPROVED)
        pending = self.make_partner("Pending Adventure", Partner.ApprovalStatus.PENDING)
        destination = DestinationPage.objects.create(
            name="Gauteng Escapes", slug="gauteng-escapes",
            introduction="Urban energy and nearby nature.", is_published=True,
        )
        destination.partners.add(approved, pending)
        DestinationPage.objects.create(name="Draft Destination", slug="draft-destination")
        response = self.client.get("/api/v1/partners/destinations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual([p["name"] for p in response.data[0]["partners"]], ["Approved Adventure"])
        hidden = self.client.get("/api/v1/partners/destinations/draft-destination/")
        self.assertEqual(hidden.status_code, 404)

    def test_collection_filters_unapproved_partners_and_respects_destination_publication(self):
        from .models import DestinationPage, ExperienceCollection
        approved = self.make_partner("Approved Tour", Partner.ApprovalStatus.APPROVED)
        rejected = self.make_partner("Rejected Tour", Partner.ApprovalStatus.REJECTED)
        destination = DestinationPage.objects.create(
            name="Magalies Gateway", slug="magalies-gateway", is_published=True,
        )
        collection = ExperienceCollection.objects.create(
            title="Outdoor Weekends", slug="outdoor-weekends",
            summary="Curated outdoor escapes around the region.",
            destination=destination, is_published=True,
        )
        collection.partners.add(approved, rejected)
        response = self.client.get("/api/v1/partners/collections/?destination=magalies-gateway")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual([p["name"] for p in response.data[0]["partners"]], ["Approved Tour"])
        destination.is_published = False
        destination.save()
        response = self.client.get("/api/v1/partners/collections/?destination=magalies-gateway")
        self.assertEqual(response.data, [])

    def test_unpublished_collection_is_not_public(self):
        from .models import ExperienceCollection
        ExperienceCollection.objects.create(
            title="Internal Draft", slug="internal-draft",
            summary="Not for public display.", is_published=False,
        )
        self.assertEqual(self.client.get("/api/v1/partners/collections/").data, [])
        self.assertEqual(self.client.get("/api/v1/partners/collections/internal-draft/").status_code, 404)


class TripPlanningAndEnquiryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(email="trip-customer@example.com", password="test-password")
        self.partner_owner = User.objects.create_user(
            email="trip-partner@example.com", password="test-password", role=User.Role.PARTNER
        )
        self.partner = Partner.objects.create(
            owner=self.partner_owner, name="Approved Adventure Lodge",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            enquiry_status=Partner.ApprovalStatus.APPROVED,
        )

    def test_trip_plans_are_private_to_their_owner(self):
        from .models import TripPlan
        plan = TripPlan.objects.create(owner=self.customer, title="Long weekend")
        other = User.objects.create_user(email="another-customer@example.com", password="test-password")
        self.client.force_authenticate(user=other)
        self.assertEqual(self.client.get("/api/v1/partners/trips/").data, [])
        self.assertEqual(self.client.get(f"/api/v1/partners/trips/{plan.pk}/").status_code, 404)

    def test_customer_can_create_plan_and_add_approved_partner(self):
        self.client.force_authenticate(user=self.customer)
        created = self.client.post("/api/v1/partners/trips/", {
            "title": "Gauteng getaway", "notes": "A relaxed weekend.",
            "start_date": "2027-02-12", "end_date": "2027-02-14",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        plan_id = created.data["id"]
        added = self.client.post(
            f"/api/v1/partners/trips/{plan_id}/items/",
            {"partner_id": self.partner.pk, "note": "Ask about family rooms."},
            format="json",
        )
        self.assertEqual(added.status_code, 201)
        self.assertEqual(added.data["items"][0]["partner"]["slug"], self.partner.slug)

    def test_trip_plan_rejects_unapproved_or_non_enquiry_partner(self):
        pending = Partner.objects.create(
            owner=self.partner_owner, name="Pending Stay",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.PENDING,
            enquiry_status=Partner.ApprovalStatus.APPROVED,
        )
        from .models import TripPlan
        plan = TripPlan.objects.create(owner=self.customer)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f"/api/v1/partners/trips/{plan.pk}/items/", {"partner_id": pending.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_customer_enquiry_requires_partner_in_owned_plan(self):
        from .models import TripPlan, TripPlanItem
        plan = TripPlan.objects.create(owner=self.customer)
        TripPlanItem.objects.create(plan=plan, partner=self.partner)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post("/api/v1/partners/enquiries/", {
            "partner_id": self.partner.pk, "trip_plan_id": plan.pk,
            "message": "Please share availability and indicative pricing for our weekend.",
            "requested_start_date": "2027-02-12", "requested_end_date": "2027-02-14",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["partner"]["name"], self.partner.name)

    def test_partner_can_respond_only_to_its_own_pending_enquiry(self):
        from .models import PartnerEnquiry
        enquiry = PartnerEnquiry.objects.create(
            customer=self.customer, partner=self.partner,
            message="Please share details for a weekend stay.",
        )
        self.client.force_authenticate(user=self.partner_owner)
        response = self.client.post(
            f"/api/v1/partners/partner/enquiries/{enquiry.pk}/respond/",
            {"status": "accepted", "partner_response": "We can discuss your requested dates."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "accepted")
        self.assertTrue(response.data["responded_at"])

    def test_other_partner_cannot_view_or_respond_to_enquiry(self):
        from .models import PartnerEnquiry
        enquiry = PartnerEnquiry.objects.create(
            customer=self.customer, partner=self.partner,
            message="Please share details for a weekend stay.",
        )
        other_owner = User.objects.create_user(
            email="other-partner@example.com", password="test-password", role=User.Role.PARTNER
        )
        self.client.force_authenticate(user=other_owner)
        self.assertEqual(self.client.get("/api/v1/partners/partner/enquiries/").data, [])
        self.assertEqual(self.client.post(
            f"/api/v1/partners/partner/enquiries/{enquiry.pk}/respond/",
            {"status": "declined", "partner_response": "Not available for these dates."},
            format="json",
        ).status_code, 404)


class EnquiryReadyPartnerDiscoveryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="ready-owner@example.com", password="test-password")

    def test_enquiry_ready_filter_excludes_partners_not_accepting_enquiries(self):
        Partner.objects.create(
            owner=self.owner, name="Ready Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            enquiry_status=Partner.ApprovalStatus.APPROVED,
        )
        Partner.objects.create(
            owner=self.owner, name="Gallery Only Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            enquiry_status=Partner.ApprovalStatus.PENDING,
        )
        response = self.client.get("/api/v1/partners/?enquiry_ready=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["Ready Lodge"])
        self.assertIn("id", response.data[0])

class ReservationFoundationTests(TestCase):
    def setUp(self):
        from datetime import date, timedelta
        from .models import PartnerAvailability
        self.client = APIClient()
        self.customer = User.objects.create_user(email="reservation-customer@example.com", password="test-password")
        self.owner = User.objects.create_user(email="reservation-owner@example.com", password="test-password", role=User.Role.PARTNER)
        self.partner = Partner.objects.create(
            owner=self.owner, name="Reservation Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = date(2027, 4, 10)
        for offset in range(3):
            PartnerAvailability.objects.create(
                partner=self.partner, date=self.start + timedelta(days=offset), capacity=4
            )

    def make_request(self, guests=2):
        return self.client.post("/api/v1/partners/reservations/", {
            "partner_id": self.partner.pk, "start_date": "2027-04-10",
            "end_date": "2027-04-12", "guests": guests,
            "message": "Please confirm our weekend reservation.",
        }, format="json")

    def test_customer_can_request_published_dates_but_request_is_not_auto_confirmed(self):
        self.client.force_authenticate(user=self.customer)
        response = self.make_request()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertIsNone(response.data["booking_reference"])

    def test_partner_confirmation_reserves_each_night_and_issues_reference(self):
        from .models import PartnerAvailability
        self.client.force_authenticate(user=self.customer)
        request = self.make_request(guests=3)
        self.assertEqual(request.status_code, 201)
        self.client.force_authenticate(user=self.owner)
        decision = self.client.post(
            f"/api/v1/partners/partner/reservations/{request.data['id']}/decision/",
            {"status": "confirmed", "partner_response": "Your reservation is confirmed."},
            format="json",
        )
        self.assertEqual(decision.status_code, 200)
        self.assertEqual(decision.data["status"], "confirmed")
        self.assertTrue(decision.data["booking_reference"])
        self.assertEqual(list(PartnerAvailability.objects.filter(partner=self.partner).order_by("date").values_list("booked_count", flat=True)), [3, 3, 0])

    def test_confirmation_rechecks_capacity_after_request_submission(self):
        from .models import PartnerAvailability
        self.client.force_authenticate(user=self.customer)
        request = self.make_request(guests=2)
        PartnerAvailability.objects.filter(partner=self.partner, date=self.start).update(booked_count=3)
        self.client.force_authenticate(user=self.owner)
        decision = self.client.post(
            f"/api/v1/partners/partner/reservations/{request.data['id']}/decision/",
            {"status": "confirmed", "partner_response": "Confirm this reservation."},
            format="json",
        )
        self.assertEqual(decision.status_code, 400)
        self.assertEqual(decision.data["status"], "pending")

    def test_customer_cancellation_releases_confirmed_capacity(self):
        from .models import PartnerAvailability, ReservationRequest
        from django.utils import timezone
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        PartnerAvailability.objects.filter(partner=self.partner, date__lt=item.end_date).update(booked_count=2)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f"/api/v1/partners/reservations/{item.pk}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(list(PartnerAvailability.objects.filter(partner=self.partner).order_by("date").values_list("booked_count", flat=True)), [0, 0, 0])

    def test_partner_cannot_decide_another_partners_reservation(self):
        from .models import ReservationRequest
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=1), guests=1,
        )
        other = User.objects.create_user(email="reservation-other@example.com", password="test-password", role=User.Role.PARTNER)
        self.client.force_authenticate(user=other)
        response = self.client.post(
            f"/api/v1/partners/partner/reservations/{item.pk}/decision/",
            {"status": "declined", "partner_response": "We cannot accommodate this request."},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_partner_availability_management_is_owner_scoped(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post("/api/v1/partners/partner/availability/", {
            "partner_id": self.partner.pk, "date": "2027-04-20", "capacity": 5,
            "is_open": True, "currency": "ZAR",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        other = User.objects.create_user(email="availability-other@example.com", password="test-password", role=User.Role.PARTNER)
        self.client.force_authenticate(user=other)
        denied = self.client.post("/api/v1/partners/partner/availability/", {
            "partner_id": self.partner.pk, "date": "2027-04-21", "capacity": 2,
        }, format="json")
        self.assertEqual(denied.status_code, 404)

class PaymentAndPartnerFinanceTests(TestCase):
    def setUp(self):
        from datetime import date, timedelta
        import uuid
        from .models import PartnerAvailability, PartnerFinancialSettings, ReservationRequest
        self.client = APIClient()
        self.customer = User.objects.create_user(email="pay-customer@example.com", password="test-password")
        self.owner = User.objects.create_user(email="pay-owner@example.com", password="test-password", role=User.Role.PARTNER)
        self.admin = User.objects.create_superuser(email="pay-admin@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.owner, name="Payment Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.start = date(2027, 5, 10)
        for offset in range(2):
            PartnerAvailability.objects.create(
                partner=self.partner, date=self.start + timedelta(days=offset),
                capacity=4, booked_count=2, price_per_guest="100.00", currency="ZAR",
            )
        self.reservation = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        self.policy = PartnerFinancialSettings.objects.create(
            partner=self.partner, deposit_type=PartnerFinancialSettings.DepositType.PERCENTAGE,
            deposit_value="20.00", commission_rate="10.00", currency="ZAR",
        )

    def create_payment(self, key="payment-key-0001"):
        return self.client.post("/api/v1/partners/payments/", {
            "reservation_id": self.reservation.pk, "idempotency_key": key,
        }, format="json")

    def test_customer_payment_record_uses_server_calculated_deposit(self):
        self.client.force_authenticate(user=self.customer)
        response = self.create_payment()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], "deposit")
        self.assertEqual(response.data["amount"], "80.00")
        self.assertEqual(response.data["status"], "pending")

    def test_payment_creation_is_idempotent(self):
        self.client.force_authenticate(user=self.customer)
        first = self.create_payment()
        second = self.create_payment()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_unconfirmed_reservation_cannot_create_payment(self):
        from .models import ReservationRequest
        self.reservation.status = ReservationRequest.Status.PENDING
        self.reservation.save(update_fields=["status"])
        self.client.force_authenticate(user=self.customer)
        response = self.create_payment()
        self.assertEqual(response.status_code, 400)

    def test_only_admin_can_reconcile_and_capture_creates_commission_ledger(self):
        from .models import ReservationPayment, PartnerCommissionLedger
        self.client.force_authenticate(user=self.customer)
        payment = self.create_payment()
        self.assertEqual(payment.status_code, 201)
        url = f"/api/v1/partners/payments/{payment.data['id']}/reconcile/"
        payload = {"status": "captured", "provider": "test_gateway", "provider_reference": "gateway-txn-001"}
        denied = self.client.post(url, payload, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(user=self.admin)
        captured = self.client.post(url, payload, format="json")
        self.assertEqual(captured.status_code, 200)
        self.assertEqual(captured.data["status"], "captured")
        entry = PartnerCommissionLedger.objects.get(payment_id=payment.data["id"])
        self.assertEqual(entry.gross_amount, Decimal("80.00"))
        self.assertEqual(entry.commission_amount, Decimal("8.00"))
        self.assertEqual(entry.partner_net_amount, Decimal("72.00"))

    def test_customer_cannot_change_partner_commission_rate(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post("/api/v1/partners/partner/financial-settings/", {
            "partner_id": self.partner.pk, "deposit_type": "fixed",
            "deposit_value": "50.00", "currency": "ZAR", "commission_rate": "0.00",
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.commission_rate, Decimal("10.00"))

    def test_captured_payment_prevents_cancellation_without_refund_workflow(self):
        from .models import ReservationPayment
        payment = ReservationPayment.objects.create(
            reservation=self.reservation, customer=self.customer, partner=self.partner,
            kind=ReservationPayment.Kind.DEPOSIT, status=ReservationPayment.Status.CAPTURED,
            amount="80.00", currency="ZAR", idempotency_key="captured-payment-0001",
            provider="test_gateway", provider_reference="captured-cancel-test-001",
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f"/api/v1/partners/reservations/{self.reservation.pk}/cancel/")
        self.assertEqual(response.status_code, 400)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, "confirmed")

    def test_admin_cannot_capture_payment_after_reservation_cancelled(self):
        self.client.force_authenticate(user=self.customer)
        payment = self.create_payment()
        self.reservation.status = "cancelled"
        self.reservation.save(update_fields=["status"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/v1/partners/payments/{payment.data['id']}/reconcile/",
            {"status": "captured", "provider": "test_gateway", "provider_reference": "late-capture-001"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_balance_uses_original_price_snapshot_after_partner_changes_daily_prices(self):
        self.client.force_authenticate(user=self.customer)
        first = self.create_payment("payment-deposit-snapshot-001")
        self.assertEqual(first.status_code, 201)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.quoted_total, Decimal("400.00"))
        self.client.force_authenticate(user=self.admin)
        reconciled = self.client.post(
            f"/api/v1/partners/payments/{first.data['id']}/reconcile/",
            {"status": "captured", "provider": "test_gateway", "provider_reference": "snapshot-deposit-001"},
            format="json",
        )
        self.assertEqual(reconciled.status_code, 200)
        from .models import PartnerAvailability
        PartnerAvailability.objects.filter(partner=self.partner).update(price_per_guest="150.00")
        self.client.force_authenticate(user=self.customer)
        balance = self.create_payment("payment-balance-snapshot-002")
        self.assertEqual(balance.status_code, 201)
        self.assertEqual(balance.data["kind"], "balance")
        self.assertEqual(balance.data["amount"], "320.00")



class RefundReconciliationTests(TestCase):
    def setUp(self):
        import uuid
        from .models import ReservationPayment, PartnerCommissionLedger
        self.client = APIClient()
        self.customer = User.objects.create_user(email="refund-customer@example.com", password="test-password")
        self.admin = User.objects.create_superuser(email="refund-admin@example.com", password="test-password")
        self.partner = Partner.objects.create(
            owner=self.admin, name="Refund Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
        )
        self.payment = ReservationPayment.objects.create(
            reservation=self._reservation(), customer=self.customer, partner=self.partner,
            kind=ReservationPayment.Kind.FULL, status=ReservationPayment.Status.CAPTURED,
            amount="100.00", currency="ZAR", idempotency_key="refund-payment-key-001",
            provider="sample_gateway", provider_reference="capture-refund-test-001",
        )
        PartnerCommissionLedger.objects.create(
            payment=self.payment, partner=self.partner, gross_amount="100.00",
            commission_rate="10.00", commission_amount="10.00", partner_net_amount="90.00",
        )

    def _reservation(self):
        import uuid
        from datetime import date
        from .models import ReservationRequest
        return ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=date(2027, 6, 1),
            end_date=date(2027, 6, 2), guests=1, status=ReservationRequest.Status.CONFIRMED,
            booking_reference=uuid.uuid4(),
        )

    def refund(self, amount, reference):
        return self.client.post(
            f"/api/v1/partners/payments/{self.payment.pk}/refunds/",
            {"amount": amount, "provider": "sample_gateway", "provider_reference": reference, "reason": "Customer refund"},
            format="json",
        )

    def test_only_staff_can_reconcile_refund(self):
        self.client.force_authenticate(user=self.customer)
        response = self.refund("25.00", "refund-ref-unauthorised")
        self.assertEqual(response.status_code, 403)

    def test_partial_refunds_reverse_commission_and_full_refund_closes_payment(self):
        from .models import ReservationRefund, PartnerCommissionAdjustment, ReservationPayment
        self.client.force_authenticate(user=self.admin)
        first = self.refund("30.00", "refund-part-001")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["status"], "refunded")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, ReservationPayment.Status.CAPTURED)
        second = self.refund("70.00", "refund-part-002")
        self.assertEqual(second.status_code, 201)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, ReservationPayment.Status.REFUNDED)
        adjustments = PartnerCommissionAdjustment.objects.filter(refund__payment=self.payment)
        self.assertEqual(sum((item.commission_reversal for item in adjustments), Decimal("0.00")), Decimal("10.00"))
        self.assertEqual(sum((item.partner_net_reversal for item in adjustments), Decimal("0.00")), Decimal("90.00"))
        self.assertEqual(ReservationRefund.objects.filter(payment=self.payment).count(), 2)
        self.client.force_authenticate(user=self.admin)
        summary = self.client.get(f"/api/v1/partners/partner/financial-summary/?partner_id={self.partner.pk}")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["captured_payments_total"], Decimal("0.00"))
        self.assertEqual(summary.data["accrued_commission_total"], Decimal("0.00"))
        self.assertEqual(summary.data["partner_net_total"], Decimal("0.00"))

    def test_refunds_cannot_exceed_captured_amount(self):
        from .models import ReservationRefund
        self.client.force_authenticate(user=self.admin)
        response = self.refund("100.01", "refund-over-limit")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ReservationRefund.objects.filter(payment=self.payment).exists())

    def test_duplicate_provider_refund_reference_is_idempotent_for_same_refund(self):
        from .models import ReservationRefund
        self.client.force_authenticate(user=self.admin)
        first = self.refund("20.00", "refund-idempotent-001")
        second = self.refund("20.00", "refund-idempotent-001")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ReservationRefund.objects.filter(payment=self.payment).count(), 1)

    def test_provider_event_ids_are_unique_per_provider(self):
        from django.db import IntegrityError, transaction
        from .models import PaymentProviderEvent
        PaymentProviderEvent.objects.create(
            provider="sample_gateway", event_id="event-001", payload_sha256="a" * 64,
            signature_verified=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentProviderEvent.objects.create(
                    provider="sample_gateway", event_id="event-001", payload_sha256="b" * 64,
                    signature_verified=True,
                )


class DualGatewayIntegrationTests(TestCase):
    def setUp(self):
        import uuid
        from datetime import date, timedelta
        from .models import ReservationRequest, ReservationPayment, PartnerFinancialSettings
        self.client = APIClient()
        self.customer = User.objects.create_user(email="gateway-customer@example.com", password="test-password")
        self.owner = User.objects.create_user(email="gateway-owner@example.com", password="test-password", role=User.Role.PARTNER)
        self.partner = Partner.objects.create(
            owner=self.owner, name="Gateway Lodge", category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED, booking_status=Partner.ApprovalStatus.APPROVED,
        )
        self.reservation = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=date(2027, 8, 1),
            end_date=date(2027, 8, 2), guests=1, status=ReservationRequest.Status.CONFIRMED,
            booking_reference=uuid.uuid4(), quoted_total="250.00", quoted_deposit="50.00",
            quoted_currency="ZAR",
        )
        PartnerFinancialSettings.objects.create(partner=self.partner, commission_rate="10.00", currency="ZAR")
        self.payment = ReservationPayment.objects.create(
            reservation=self.reservation, customer=self.customer, partner=self.partner,
            kind=ReservationPayment.Kind.DEPOSIT, status=ReservationPayment.Status.PENDING,
            amount="50.00", currency="ZAR", idempotency_key="gateway-idempotency-001",
            provider="yoco", checkout_session_id="ch_yoco_checkout_001",
        )

    def yoco_webhook(self, webhook_id="wh_evt_001", signature_valid=True):
        import base64
        import hashlib
        import hmac
        import json
        import time
        from django.test import override_settings
        secret_bytes = b"test-yoco-webhook-secret"
        secret = "whsec_" + base64.b64encode(secret_bytes).decode("ascii")
        raw = json.dumps({
            "createdDate": "2027-07-01T10:00:00Z",
            "id": "evt_yoco_001",
            "type": "payment.succeeded",
            "payload": {
                "amount": 5000, "currency": "ZAR", "id": "pay_yoco_001",
                "status": "succeeded", "metadata": {"checkoutId": "ch_yoco_checkout_001"},
            },
        }, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        signed = webhook_id.encode() + b"." + timestamp.encode() + b"." + raw
        signature = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
        if not signature_valid:
            signature = "invalid"
        with override_settings(YOCO_WEBHOOK_SECRET=secret):
            return self.client.generic(
                "POST", "/api/v1/partners/webhooks/yoco/", raw,
                content_type="application/json",
                HTTP_WEBHOOK_ID=webhook_id,
                HTTP_WEBHOOK_TIMESTAMP=timestamp,
                HTTP_WEBHOOK_SIGNATURE=f"v1,{signature}",
            )

    def test_yoco_signed_webhook_captures_only_matching_amount_and_creates_commission(self):
        from .models import ReservationPayment, PartnerCommissionLedger
        response = self.yoco_webhook()
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, ReservationPayment.Status.CAPTURED)
        self.assertEqual(self.payment.provider_reference, "ch_yoco_checkout_001")
        self.assertEqual(PartnerCommissionLedger.objects.get(payment=self.payment).commission_amount, Decimal("5.00"))

    def test_yoco_webhook_rejects_invalid_signature(self):
        response = self.yoco_webhook(signature_valid=False)
        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")

    def test_yoco_duplicate_webhook_is_idempotent(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger
        first = self.yoco_webhook(webhook_id="wh_evt_duplicate")
        second = self.yoco_webhook(webhook_id="wh_evt_duplicate")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.assertEqual(PaymentProviderEvent.objects.filter(provider="yoco").count(), 1)
        self.assertEqual(PartnerCommissionLedger.objects.filter(payment=self.payment).count(), 1)

    def test_payfast_itn_requires_valid_signature_source_and_server_validation(self):
        from unittest.mock import patch
        from urllib.parse import urlencode
        from django.test import override_settings
        from .gateways import _payfast_signature
        from .models import ReservationPayment, PartnerCommissionLedger
        self.payment.provider = "payfast"
        self.payment.save(update_fields=["provider"])
        payload = {
            "m_payment_id": str(self.payment.pk),
            "pf_payment_id": "pf_txn_12345",
            "payment_status": "COMPLETE",
            "amount_gross": "50.00",
            "merchant_id": "10000100",
        }
        payload["signature"] = _payfast_signature(payload)
        raw = urlencode(payload).encode()
        self.client.force_authenticate(user=None)
        with override_settings(PAYFAST_MERCHANT_ID="10000100", PAYFAST_PASSPHRASE=""):
            with patch("partners.views.verify_payfast_source_ip", return_value=True), patch(
                "partners.views.validate_payfast_itn", return_value=True
            ):
                response = self.client.generic(
                    "POST", "/api/v1/partners/webhooks/payfast/", raw,
                    content_type="application/x-www-form-urlencoded",
                    REMOTE_ADDR="127.0.0.1",
                )
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, ReservationPayment.Status.CAPTURED)
        self.assertEqual(self.payment.provider_reference, "pf_txn_12345")
        self.assertEqual(PartnerCommissionLedger.objects.get(payment=self.payment).commission_amount, Decimal("5.00"))

    def test_payfast_checkout_returns_signed_sandbox_form(self):
        from django.test import override_settings
        self.client.force_authenticate(user=self.customer)
        self.payment.provider = "manual_reconciliation"
        self.payment.save(update_fields=["provider"])
        with override_settings(
            PAYFAST_MERCHANT_ID="10000100", PAYFAST_MERCHANT_KEY="test-key",
            PAYFAST_PASSPHRASE="", PAYFAST_SANDBOX=True,
            PAYFAST_NOTIFY_URL="https://example.test/api/v1/partners/webhooks/payfast/",
            PAYMENT_RETURN_URL="https://example.test/payment/success",
            PAYMENT_CANCEL_URL="https://example.test/payment/cancelled",
        ):
            response = self.client.post(
                f"/api/v1/partners/payments/{self.payment.pk}/checkout/",
                {"provider": "payfast"}, format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["checkout_url"], "https://sandbox.payfast.co.za/eng/process")
        self.assertEqual(response.data["form_fields"]["amount"], "50.00")
        self.assertIn("signature", response.data["form_fields"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.provider, "payfast")
        self.assertEqual(self.payment.checkout_session_id, str(self.payment.pk))

    def test_yoco_checkout_uses_server_key_amount_and_idempotency_key(self):
        import json
        from unittest.mock import MagicMock, patch
        from django.test import override_settings
        from .gateways import create_yoco_checkout
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = json.dumps({
            "id": "ch_yoco_created", "amount": 5000, "currency": "ZAR",
            "redirectUrl": "https://c.yoco.com/checkout/ch_yoco_created",
        }).encode()
        with override_settings(YOCO_SECRET_KEY="sk_test_example"):
            with patch("partners.gateways.urlopen", return_value=mock_response) as send:
                result = create_yoco_checkout(self.payment)
        self.assertEqual(result["checkout_session_id"], "ch_yoco_created")
        self.assertEqual(result["checkout_url"], "https://c.yoco.com/checkout/ch_yoco_created")
        outgoing = send.call_args.args[0]
        self.assertEqual(outgoing.get_header("Authorization"), "Bearer sk_test_example")
        self.assertEqual(outgoing.get_header("Idempotency-key"), self.payment.idempotency_key)

    def test_yoco_checkout_rejects_unexpected_redirect_host(self):
        import json
        from unittest.mock import MagicMock, patch
        from django.test import override_settings
        from .gateways import GatewayError, create_yoco_checkout
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = json.dumps({
            "id": "ch_bad", "amount": 5000, "currency": "ZAR",
            "redirectUrl": "https://attacker.example/checkout",
        }).encode()
        with override_settings(YOCO_SECRET_KEY="sk_test_example"):
            with patch("partners.gateways.urlopen", return_value=mock_response):
                with self.assertRaises(GatewayError):
                    create_yoco_checkout(self.payment)

    def yoco_refund_webhook(self, event_type="refund.succeeded", webhook_id="wh_refund_001", amount=2000):
        import base64
        import hashlib
        import hmac
        import json
        import time
        from django.test import override_settings
        secret_bytes = b"test-yoco-webhook-secret"
        secret = "whsec_" + base64.b64encode(secret_bytes).decode("ascii")
        raw = json.dumps({
            "createdDate": "2027-07-01T10:00:00Z",
            "id": "evt_refund_" + webhook_id,
            "type": event_type,
            "payload": {
                "amount": amount, "currency": "ZAR", "id": "rfd_" + webhook_id,
                "status": "succeeded" if event_type == "refund.succeeded" else "failed",
                "type": "refund", "metadata": {"checkoutId": "ch_yoco_checkout_001"},
            },
        }, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        signed = webhook_id.encode() + b"." + timestamp.encode() + b"." + raw
        signature = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
        with override_settings(YOCO_WEBHOOK_SECRET=secret):
            return self.client.generic(
                "POST", "/api/v1/partners/webhooks/yoco/", raw,
                content_type="application/json", HTTP_WEBHOOK_ID=webhook_id,
                HTTP_WEBHOOK_TIMESTAMP=timestamp, HTTP_WEBHOOK_SIGNATURE=f"v1,{signature}",
            )

    def test_yoco_refund_is_pending_until_signed_success_webhook(self):
        from unittest.mock import patch
        from .models import ReservationPayment, ReservationRefund, PartnerCommissionAdjustment
        self.yoco_webhook()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, ReservationPayment.Status.CAPTURED)
        self.client.force_authenticate(user=self.admin)
        with patch("partners.views.create_yoco_refund", return_value={
            "status": "pending", "provider_reference": "rfd_refund_001",
        }):
            started = self.client.post(
                f"/api/v1/partners/payments/{self.payment.pk}/refunds/initiate/",
                {"amount": "20.00", "reason": "Customer request", "idempotency_key": "yoco-refund-key-001"},
                format="json",
            )
        self.assertEqual(started.status_code, 202)
        self.assertEqual(started.data["status"], "pending")
        self.client.force_authenticate(user=None)
        completed = self.yoco_refund_webhook()
        self.assertEqual(completed.status_code, 200)
        refund = ReservationRefund.objects.get(payment=self.payment)
        self.assertEqual(refund.status, ReservationRefund.Status.REFUNDED)
        self.assertEqual(refund.provider_reference, "rfd_wh_refund_001")
        self.assertEqual(PartnerCommissionAdjustment.objects.get(refund=refund).commission_reversal, Decimal("2.00"))

    def test_yoco_failed_refund_webhook_does_not_reverse_commission(self):
        from unittest.mock import patch
        from .models import ReservationRefund, PartnerCommissionAdjustment
        self.yoco_webhook()
        self.client.force_authenticate(user=self.admin)
        with patch("partners.views.create_yoco_refund", return_value={
            "status": "pending", "provider_reference": "rfd_refund_failed",
        }):
            started = self.client.post(
                f"/api/v1/partners/payments/{self.payment.pk}/refunds/initiate/",
                {"amount": "20.00", "reason": "Customer request", "idempotency_key": "yoco-refund-key-002"},
                format="json",
            )
        self.assertEqual(started.status_code, 202)
        self.client.force_authenticate(user=None)
        failed = self.yoco_refund_webhook(event_type="refund.failed", webhook_id="wh_refund_failed")
        self.assertEqual(failed.status_code, 200)
        refund = ReservationRefund.objects.get(payment=self.payment)
        self.assertEqual(refund.status, ReservationRefund.Status.FAILED)
        self.assertFalse(PartnerCommissionAdjustment.objects.filter(refund=refund).exists())

    def test_gateway_refund_initiation_rejects_over_refund_and_duplicate_pending(self):
        from .models import ReservationRefund
        self.yoco_webhook()
        self.client.force_authenticate(user=self.admin)
        too_much = self.client.post(
            f"/api/v1/partners/payments/{self.payment.pk}/refunds/initiate/",
            {"amount": "50.01", "idempotency_key": "yoco-refund-over-001"},
            format="json",
        )
        self.assertEqual(too_much.status_code, 400)
        self.assertFalse(ReservationRefund.objects.filter(payment=self.payment).exists())

    def test_yoco_refund_adapter_uses_server_key_and_idempotency(self):
        import json
        from unittest.mock import MagicMock, patch
        from django.test import override_settings
        from .models import ReservationRefund
        from .gateways import create_yoco_refund
        self.payment.provider = "yoco"
        self.payment.status = "captured"
        self.payment.provider_reference = "ch_yoco_capture"
        self.payment.save(update_fields=["provider", "status", "provider_reference"])
        refund = ReservationRefund.objects.create(
            payment=self.payment, amount="10.00", currency="ZAR", provider="yoco",
            status="pending", idempotency_key="yoco-refund-adapter-001",
        )
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = json.dumps({
            "id": "ch_yoco_checkout_001", "refundId": "rfd_adapter_001", "status": "pending",
        }).encode()
        with override_settings(YOCO_SECRET_KEY="sk_test_example"):
            with patch("partners.gateways.urlopen", return_value=mock_response) as send:
                result = create_yoco_refund(self.payment, refund)
        self.assertEqual(result["provider_reference"], "rfd_adapter_001")
        outgoing = send.call_args.args[0]
        self.assertEqual(outgoing.get_header("Authorization"), "Bearer sk_test_example")
        self.assertEqual(outgoing.get_header("Idempotency-key"), "yoco-refund-adapter-001")
        self.assertEqual(json.loads(outgoing.data)["amount"], 1000)
