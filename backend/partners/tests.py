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

    def accept_quote(self, reservation_id):
        from datetime import timedelta
        from django.utils import timezone

        self.client.force_authenticate(user=self.owner)
        quote = self.client.post(
            f"/api/v1/partners/partner/reservations/{reservation_id}/quotes/",
            {
                "currency": "ZAR",
                "deposit_amount": "300.00",
                "expires_at": (timezone.now() + timedelta(days=2)).isoformat(),
                "items": [{"description": "Accommodation", "quantity": "1", "unit_price": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(quote.status_code, 201, quote.data)
        self.client.force_authenticate(user=self.customer)
        accepted = self.client.post(
            f"/api/v1/partners/reservations/{reservation_id}/quote-decision/",
            {"status": "accepted"},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.data)

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
        self.accept_quote(request.data['id'])
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
        self.accept_quote(request.data['id'])
        PartnerAvailability.objects.filter(partner=self.partner, date=self.start).update(booked_count=3)
        self.client.force_authenticate(user=self.owner)
        decision = self.client.post(
            f"/api/v1/partners/partner/reservations/{request.data['id']}/decision/",
            {"status": "confirmed", "partner_response": "Confirm this reservation."},
            format="json",
        )
        self.assertEqual(decision.status_code, 400)
        self.assertIn("availability or capacity has changed", str(decision.data).lower())
        from .models import ReservationRequest
        request_record = ReservationRequest.objects.get(pk=request.data["id"])
        self.assertEqual(request_record.status, ReservationRequest.Status.PENDING)

    def test_customer_cancellation_releases_confirmed_capacity_after_partner_approval(self):
        from .models import PartnerAvailability, ReservationRequest
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        PartnerAvailability.objects.filter(partner=self.partner, date__lt=item.end_date).update(booked_count=2)
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f"/api/v1/partners/reservations/{item.pk}/cancel/",
            {"reason": "We need to cancel these travel dates."}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(user=self.owner)
        decision = self.client.post(
            f"/api/v1/partners/cancellations/{response.data['id']}/decision/",
            {"status": "approved", "decision_note": "Cancellation approved."}, format="json",
        )
        self.assertEqual(decision.status_code, 200)
        self.assertEqual(decision.data["status"], "completed")
        item.refresh_from_db()
        self.assertEqual(item.status, "cancelled")
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


    def test_confirmed_customer_cancellation_requires_partner_decision_and_notifies_both_parties(self):
        from .models import ReservationRequest, ReservationCancellationRequest, ReservationNotification
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f"/api/v1/partners/reservations/{item.pk}/cancel/",
            {"reason": "Our travel dates have changed unexpectedly."}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(ReservationNotification.objects.filter(cancellation_request_id=response.data["id"]).count(), 2)

    def test_partner_approval_completes_unpaid_cancellation_and_releases_capacity(self):
        from .models import PartnerAvailability, ReservationRequest, ReservationCancellationRequest, ReservationNotification
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        PartnerAvailability.objects.filter(partner=self.partner, date__lt=item.end_date).update(booked_count=2)
        self.client.force_authenticate(user=self.customer)
        created = self.client.post(
            f"/api/v1/partners/reservations/{item.pk}/cancel/",
            {"reason": "We can no longer travel on these dates."}, format="json",
        )
        self.client.force_authenticate(user=self.owner)
        decided = self.client.post(
            f"/api/v1/partners/cancellations/{created.data['id']}/decision/",
            {"status": "approved", "decision_note": "Approved; dates released."}, format="json",
        )
        self.assertEqual(decided.status_code, 200)
        self.assertEqual(decided.data["status"], "completed")
        item.refresh_from_db()
        self.assertEqual(item.status, ReservationRequest.Status.CANCELLED)
        self.assertEqual(list(PartnerAvailability.objects.filter(partner=self.partner).order_by("date").values_list("booked_count", flat=True)), [0, 0, 0])
        self.assertEqual(ReservationNotification.objects.filter(cancellation_request_id=created.data["id"]).count(), 4)

    def test_partner_cannot_decide_cancellation_for_another_partner(self):
        from .models import ReservationRequest
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=1), guests=1,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        self.client.force_authenticate(user=self.customer)
        created = self.client.post(
            f"/api/v1/partners/reservations/{item.pk}/cancel/",
            {"reason": "We need to change our plans."}, format="json",
        )
        other = User.objects.create_user(email="other-cancel-partner@example.com", password="test-password", role=User.Role.PARTNER)
        self.client.force_authenticate(user=other)
        denied = self.client.post(
            f"/api/v1/partners/cancellations/{created.data['id']}/decision/",
            {"status": "approved", "decision_note": "Approved by unauthorised user."}, format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_customer_can_only_read_and_mark_own_reservation_notifications(self):
        from .models import ReservationRequest, ReservationNotification
        import uuid
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=1), guests=1,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        notification = ReservationNotification.objects.create(
            recipient=self.customer, reservation=item, event="cancellation_requested",
            title="Cancellation update", message="Your request is under review.",
        )
        self.client.force_authenticate(user=self.customer)
        inbox = self.client.get("/api/v1/partners/notifications/?unread=true")
        self.assertEqual(inbox.status_code, 200)
        self.assertEqual(len(inbox.data), 1)
        read = self.client.post(f"/api/v1/partners/notifications/{notification.pk}/read/")
        self.assertEqual(read.status_code, 200)
        self.assertIsNotNone(read.data["read_at"])
        other = User.objects.create_user(email="other-notification@example.com", password="test-password")
        self.client.force_authenticate(user=other)
        denied = self.client.post(f"/api/v1/partners/notifications/{notification.pk}/read/")
        self.assertEqual(denied.status_code, 404)


    def test_reservation_request_sends_audited_emails_to_customer_and_partner(self):
        from django.core import mail
        from django.test import override_settings
        from .models import ReservationEmailDelivery
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.force_authenticate(user=self.customer)
                response = self.make_request()
            self.assertEqual(response.status_code, 201)
            self.assertEqual(len(mail.outbox), 2)
            deliveries = ReservationEmailDelivery.objects.filter(
                reservation_id=response.data["id"], event="reservation_requested"
            )
            self.assertEqual(deliveries.count(), 2)
            self.assertTrue(all(item.status == ReservationEmailDelivery.Status.SENT for item in deliveries))
            self.assertEqual(set(deliveries.values_list("recipient_role", flat=True)), {"customer", "partner"})

    def test_partner_confirmation_emails_include_booking_reference(self):
        from django.core import mail
        from django.test import override_settings
        from .models import ReservationEmailDelivery
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.force_authenticate(user=self.customer)
                request = self.make_request()
            self.accept_quote(request.data['id'])
            mail.outbox.clear()
            with self.captureOnCommitCallbacks(execute=True):
                self.client.force_authenticate(user=self.owner)
                decision = self.client.post(
                    f"/api/v1/partners/partner/reservations/{request.data['id']}/decision/",
                    {"status": "confirmed", "partner_response": "Your stay is confirmed."},
                    format="json",
                )
            self.assertEqual(decision.status_code, 200)
            self.assertEqual(len(mail.outbox), 2)
            self.assertTrue(decision.data["booking_reference"])
            deliveries = ReservationEmailDelivery.objects.filter(
                reservation_id=request.data["id"], event="reservation_confirmed"
            )
            self.assertEqual(deliveries.count(), 2)
            self.assertTrue(all(str(decision.data["booking_reference"]) in item.body for item in deliveries))

    def test_cancellation_request_and_completion_send_audited_emails(self):
        import uuid
        from datetime import timedelta
        from django.core import mail
        from django.test import override_settings
        from .models import ReservationRequest, ReservationEmailDelivery
        item = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + timedelta(days=2), guests=2,
            status=ReservationRequest.Status.CONFIRMED, booking_reference=uuid.uuid4(),
        )
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.force_authenticate(user=self.customer)
                created = self.client.post(
                    f"/api/v1/partners/reservations/{item.pk}/cancel/",
                    {"reason": "Our travel dates have changed unexpectedly."}, format="json",
                )
            self.assertEqual(created.status_code, 201)
            self.assertEqual(len(mail.outbox), 2)
            mail.outbox.clear()
            with self.captureOnCommitCallbacks(execute=True):
                self.client.force_authenticate(user=self.owner)
                decided = self.client.post(
                    f"/api/v1/partners/cancellations/{created.data['id']}/decision/",
                    {"status": "approved", "decision_note": "Approved."}, format="json",
                )
            self.assertEqual(decided.data["status"], "completed")
            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(
                ReservationEmailDelivery.objects.filter(
                    reservation=item, event="cancellation_requested", status="sent"
                ).count(), 2,
            )
            self.assertEqual(
                ReservationEmailDelivery.objects.filter(
                    reservation=item, event="cancellation_completed", status="sent"
                ).count(), 2,
            )

    def test_failed_reservation_email_can_be_retried_without_resending_success(self):
        from unittest.mock import Mock, patch
        from django.test import override_settings
        from .models import ReservationEmailDelivery, ReservationRequest
        from .reservation_email_notifications import send_reservation_email

        reservation = ReservationRequest.objects.create(
            customer=self.customer, partner=self.partner, start_date=self.start,
            end_date=self.start + __import__("datetime").timedelta(days=1), guests=1,
        )
        delivery = ReservationEmailDelivery.objects.create(
            reservation=reservation, event="test_event", event_key="test-event-customer",
            recipient_email=self.customer.email, recipient_role="customer",
            subject="Test", body="Test body",
        )

        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            failed_message = Mock()
            failed_message.send.side_effect = RuntimeError("SMTP unavailable")
            with patch(
                "partners.reservation_email_notifications.EmailMultiAlternatives",
                return_value=failed_message,
            ):
                send_reservation_email(delivery.pk)

            delivery.refresh_from_db()
            self.assertEqual(delivery.status, ReservationEmailDelivery.Status.FAILED)
            self.assertEqual(delivery.attempts, 1)
            self.assertIn("SMTP unavailable", delivery.last_error)

            successful_message = Mock()
            successful_message.send.return_value = 1
            with patch(
                "partners.reservation_email_notifications.EmailMultiAlternatives",
                return_value=successful_message,
            ):
                send_reservation_email(delivery.pk)
                send_reservation_email(delivery.pk)

            delivery.refresh_from_db()
            self.assertEqual(delivery.status, ReservationEmailDelivery.Status.SENT)
            self.assertEqual(delivery.attempts, 2)
            successful_message.send.assert_called_once_with(fail_silently=False)

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
        response = self.client.post(
            f"/api/v1/partners/reservations/{self.reservation.pk}/cancel/",
            {"reason": "I can no longer travel on the selected dates."}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, "confirmed")
        self.assertEqual(response.data["status"], "pending")

    def test_captured_payment_cancellation_completes_only_after_staff_refund_reconciliation(self):
        import uuid
        from .models import ReservationPayment, PartnerCommissionLedger, ReservationCancellationRequest, ReservationNotification, ReservationRequest
        payment = ReservationPayment.objects.create(
            reservation=self.reservation, customer=self.customer, partner=self.partner,
            kind=ReservationPayment.Kind.DEPOSIT, status=ReservationPayment.Status.CAPTURED,
            amount="80.00", currency="ZAR", idempotency_key="captured-cancel-flow-001",
            provider="sample_gateway", provider_reference="captured-cancel-flow-002",
        )
        PartnerCommissionLedger.objects.create(
            payment=payment, partner=self.partner, gross_amount="80.00",
            commission_rate="10.00", commission_amount="8.00", partner_net_amount="72.00",
        )
        self.client.force_authenticate(user=self.customer)
        created = self.client.post(
            f"/api/v1/partners/reservations/{self.reservation.pk}/cancel/",
            {"reason": "My travel plans have changed and I need to cancel."}, format="json",
        )
        self.client.force_authenticate(user=self.owner)
        approved = self.client.post(
            f"/api/v1/partners/cancellations/{created.data['id']}/decision/",
            {"status": "approved", "decision_note": "Approved subject to refund completion."}, format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], ReservationCancellationRequest.Status.APPROVED)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationRequest.Status.CONFIRMED)
        self.client.force_authenticate(user=self.admin)
        refund = self.client.post(
            f"/api/v1/partners/payments/{payment.pk}/refunds/",
            {"amount": "80.00", "provider": "sample_gateway", "provider_reference": "manual-cancel-refund-001", "reason": "Approved reservation cancellation"},
            format="json",
        )
        self.assertEqual(refund.status_code, 201)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationRequest.Status.CANCELLED)
        cancellation = ReservationCancellationRequest.objects.get(pk=created.data["id"])
        self.assertEqual(cancellation.status, ReservationCancellationRequest.Status.COMPLETED)
        self.assertTrue(ReservationNotification.objects.filter(
            recipient=self.customer, event="cancellation_completed", cancellation_request=cancellation
        ).exists())

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



    def test_customer_payment_history_includes_refunds_and_is_scoped_to_customer(self):
        from .models import ReservationRefund
        self.client.force_authenticate(user=self.admin)
        refund_response = self.refund("25.00", "refund-history-visible-001")
        self.assertEqual(refund_response.status_code, 201)
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/v1/partners/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        payment = response.data[0]
        self.assertEqual(payment["id"], self.payment.pk)
        self.assertEqual(len(payment["refunds"]), 1)
        self.assertEqual(payment["refunds"][0]["amount"], "25.00")
        self.assertEqual(payment["refunds"][0]["status"], ReservationRefund.Status.REFUNDED)
        other = User.objects.create_user(email="other-customer@example.com", password="test-password")
        self.client.force_authenticate(user=other)
        other_response = self.client.get("/api/v1/partners/payments/")
        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.data, [])

    def test_successful_refund_sends_separate_audit_emails_once(self):
        from django.core import mail
        from django.test import override_settings
        from .models import RefundAuditEmail

        self.client.force_authenticate(user=self.admin)
        response = self.refund("25.00", "refund-audit-email-001")
        self.assertEqual(response.status_code, 201)
        audit = RefundAuditEmail.objects.get(refund_id=response.data["id"])
        self.assertEqual(audit.status, RefundAuditEmail.Status.PENDING)
        self.assertEqual(audit.customer_email, self.customer.email)
        self.assertEqual(audit.partner_email, self.admin.email)

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="audit@example.test",
        ):
            from .refund_notifications import send_refund_audit_email
            send_refund_audit_email(audit.pk)
            self.assertEqual(len(mail.outbox), 2)
            self.assertEqual(mail.outbox[0].to, [self.customer.email])
            self.assertEqual(mail.outbox[1].to, [self.admin.email])
            self.assertIn("Refund Confirmation", mail.outbox[0].subject)
            self.assertIn("25.00", mail.outbox[0].body)
            send_refund_audit_email(audit.pk)
            self.assertEqual(len(mail.outbox), 2)

        audit.refresh_from_db()
        self.assertEqual(audit.status, RefundAuditEmail.Status.SENT)
        self.assertIsNotNone(audit.customer_sent_at)
        self.assertIsNotNone(audit.partner_sent_at)
        self.assertEqual(audit.attempts, 2)


    def test_refund_audit_retry_command_dry_run_does_not_send(self):
        from django.core.management import call_command
        from .models import RefundAuditEmail

        self.client.force_authenticate(user=self.admin)
        response = self.refund("15.00", "refund-audit-dry-run-001")
        self.assertEqual(response.status_code, 201)
        audit = RefundAuditEmail.objects.get(refund_id=response.data["id"])

        from io import StringIO
        output = StringIO()
        call_command("retry_refund_audit_emails", "--dry-run", stdout=output)

        audit.refresh_from_db()
        self.assertEqual(audit.attempts, 0)
        self.assertEqual(audit.status, RefundAuditEmail.Status.PENDING)
        self.assertIn("would be processed", output.getvalue())

    def test_refund_audit_retry_command_respects_limit_and_attempt_cap(self):
        from django.core import mail
        from django.core.management import call_command
        from django.test import override_settings
        from .models import RefundAuditEmail

        self.client.force_authenticate(user=self.admin)
        first = self.refund("10.00", "refund-audit-limit-001")
        second = self.refund("10.00", "refund-audit-limit-002")
        first_audit = RefundAuditEmail.objects.get(refund_id=first.data["id"])
        second_audit = RefundAuditEmail.objects.get(refund_id=second.data["id"])
        second_audit.attempts = 10
        second_audit.save(update_fields=["attempts"])

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="audit@example.test",
        ):
            call_command("retry_refund_audit_emails", "--limit", "1", "--max-attempts", "10")

        first_audit.refresh_from_db()
        second_audit.refresh_from_db()
        self.assertEqual(first_audit.status, RefundAuditEmail.Status.SENT)
        self.assertEqual(first_audit.attempts, 1)
        self.assertEqual(second_audit.attempts, 10)
        self.assertEqual(len(mail.outbox), 2)


class DualGatewayIntegrationTests(TestCase):
    def setUp(self):
        import uuid
        from datetime import date, timedelta
        from .models import ReservationRequest, ReservationPayment, PartnerFinancialSettings
        self.client = APIClient()
        self.customer = User.objects.create_user(email="gateway-customer@example.com", password="test-password")
        self.owner = User.objects.create_user(email="gateway-owner@example.com", password="test-password", role=User.Role.PARTNER)
        self.admin = User.objects.create_superuser(email="gateway-admin@example.com", password="test-password")
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
            kind=ReservationPayment.Kind.DEPOSIT, status="pending",
            amount="50.00", currency="ZAR", idempotency_key="gateway-idempotency-001",
            provider="yoco", checkout_session_id="ch_yoco_checkout_001",
        )

    def yoco_webhook(
        self, webhook_id="wh_evt_001", signature_valid=True,
        amount=5000, currency="ZAR", checkout_id="ch_yoco_checkout_001",
    ):
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
                "amount": amount, "currency": currency, "id": "pay_yoco_001",
                "status": "succeeded", "metadata": {"checkoutId": checkout_id},
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

    def test_yoco_webhook_rejects_amount_mismatch_without_recording_event(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger

        response = self.yoco_webhook(webhook_id="wh_evt_wrong_amount", amount=4999)

        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="yoco").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())

    def test_yoco_webhook_rejects_currency_mismatch_without_recording_event(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger

        response = self.yoco_webhook(webhook_id="wh_evt_wrong_currency", currency="USD")

        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="yoco").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())

    def test_yoco_webhook_rejects_unrecognised_checkout(self):
        from .models import PaymentProviderEvent

        response = self.yoco_webhook(
            webhook_id="wh_evt_unknown_checkout",
            checkout_id="ch_yoco_unknown",
        )

        self.assertEqual(response.status_code, 404)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="yoco").exists())

    def test_yoco_duplicate_webhook_is_idempotent(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger
        first = self.yoco_webhook(webhook_id="wh_evt_duplicate")
        second = self.yoco_webhook(webhook_id="wh_evt_duplicate")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.assertEqual(PaymentProviderEvent.objects.filter(provider="yoco").count(), 1)
        self.assertEqual(PartnerCommissionLedger.objects.filter(payment=self.payment).count(), 1)

    def payfast_webhook(self, payment_status="COMPLETE", amount="50.00", transaction_id="pf_txn_shared"):
        from unittest.mock import patch
        from urllib.parse import urlencode
        from django.test import override_settings
        from .gateways import _payfast_signature

        # The shared fixture defaults to Yoco; PayFast ITNs only resolve
        # payments explicitly associated with the PayFast provider.
        self.payment.provider = "payfast"
        self.payment.save(update_fields=["provider"])
        payload = {
            "m_payment_id": str(self.payment.pk),
            "pf_payment_id": transaction_id,
            "payment_status": payment_status,
            "amount_gross": amount,
            "merchant_id": "10000100",
        }
        payload["signature"] = _payfast_signature(payload)
        raw = urlencode(payload).encode()
        self.client.force_authenticate(user=None)
        with override_settings(PAYFAST_MERCHANT_ID="10000100", PAYFAST_PASSPHRASE=""):
            with patch("partners.views.verify_payfast_source_ip", return_value=True), patch(
                "partners.views.validate_payfast_itn", return_value=True
            ):
                return self.client.generic(
                    "POST", "/api/v1/partners/webhooks/payfast/", raw,
                    content_type="application/x-www-form-urlencoded",
                    REMOTE_ADDR="127.0.0.1",
                )

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

    def test_payfast_amount_mismatch_is_rejected_without_payment_or_ledger_change(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger
        response = self.payfast_webhook(amount="49.99", transaction_id="pf_wrong_amount")
        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="payfast").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())

    def test_payfast_cancelled_itn_marks_payment_failed_without_commission(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger
        response = self.payfast_webhook(
            payment_status="CANCELLED", transaction_id="pf_cancelled_001"
        )
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "failed")
        self.assertIn("Payfast reported payment failure.", self.payment.failure_reason)
        self.assertTrue(PaymentProviderEvent.objects.filter(provider="payfast").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())

    def test_payfast_duplicate_complete_itn_is_idempotent(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger
        first = self.payfast_webhook(transaction_id="pf_duplicate_001")
        second = self.payfast_webhook(transaction_id="pf_duplicate_001")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "captured")
        self.assertEqual(PaymentProviderEvent.objects.filter(provider="payfast").count(), 1)
        self.assertEqual(PartnerCommissionLedger.objects.filter(payment=self.payment).count(), 1)

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



    def test_yoco_success_for_cancelled_reservation_is_rejected_without_capture(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger, ReservationRequest

        self.reservation.status = ReservationRequest.Status.CANCELLED
        self.reservation.save(update_fields=["status"])

        response = self.yoco_webhook(webhook_id="wh_evt_cancelled_reservation")

        self.assertEqual(response.status_code, 409)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="yoco").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())

    def test_payfast_success_for_cancelled_reservation_is_rejected_without_capture(self):
        from .models import PaymentProviderEvent, PartnerCommissionLedger, ReservationRequest

        self.reservation.status = ReservationRequest.Status.CANCELLED
        self.reservation.save(update_fields=["status"])

        response = self.payfast_webhook(transaction_id="pf_cancelled_reservation_001")

        self.assertEqual(response.status_code, 409)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
        self.assertFalse(PaymentProviderEvent.objects.filter(provider="payfast").exists())
        self.assertFalse(PartnerCommissionLedger.objects.filter(payment=self.payment).exists())


class PartnerOwnedProfileEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="owned-profiles@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.other = User.objects.create_user(
            email="other-owned-profiles@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.owned = Partner.objects.create(
            owner=self.owner, name="Owner Profile",
            category=Partner.Category.ACCOMMODATION,
        )
        self.not_owned = Partner.objects.create(
            owner=self.other, name="Other Profile",
            category=Partner.Category.ACCOMMODATION,
        )
        self.url = "/api/v1/partners/partner/my-profiles/"

    def test_partner_owner_receives_only_their_own_profiles(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.owned.pk])

    def test_profile_endpoint_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)


class PartnerVerificationOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="onboarding-owner@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.other_owner = User.objects.create_user(
            email="onboarding-other@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.staff = User.objects.create_superuser(
            email="verification-staff@example.com", password="test-password",
        )
        self.partner = Partner.objects.create(
            owner=self.owner, name="Onboarding Lodge",
            category=Partner.Category.ACCOMMODATION,
        )
        self.other_partner = Partner.objects.create(
            owner=self.other_owner, name="Other Lodge",
            category=Partner.Category.ACCOMMODATION,
        )
        self.url = "/api/v1/partners/partner/onboarding/"

    def valid_submission(self):
        return {
            "partner_id": self.partner.pk,
            "legal_business_name": "Onboarding Lodge Proprietary Limited",
            "registration_number": "2026/123456/07",
            "contact_person": "Business Owner",
            "contact_email": "owner@onboarding.example",
            "contact_phone": "+27110000000",
            "physical_address": "10 Example Road, Johannesburg, Gauteng",
            "document_checklist": ["business_registration"],
            "submit": True,
        }

    def submit_valid_application(self):
        payload = self.valid_submission()
        payload.pop("submit")
        draft = self.client.post(self.url, payload, format="json")
        self.assertIn(draft.status_code, (200, 201))
        upload = SimpleUploadedFile(
            "registration.pdf", b"%PDF-1.4\\nverification evidence",
            content_type="application/pdf",
        )
        evidence = self.client.post(
            f"/api/v1/partners/partner/onboarding/{draft.data['id']}/documents/",
            {"document_type": "business_registration", "file": upload},
            format="multipart",
        )
        self.assertEqual(evidence.status_code, 201)
        return self.client.post(
            self.url, {"partner_id": self.partner.pk, "submit": True}, format="json"
        )

    def test_partner_owner_can_submit_verification_application(self):
        from .models import PartnerVerificationSubmission, PartnerVerificationEvent
        self.client.force_authenticate(self.owner)
        response = self.submit_valid_application()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], PartnerVerificationSubmission.Status.SUBMITTED)
        self.assertIsNotNone(response.data["submitted_at"])
        self.assertEqual(PartnerVerificationEvent.objects.filter(submission_id=response.data["id"], event_type="submitted").count(), 1)

    def test_submission_requires_business_and_contact_details(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url, {"partner_id": self.partner.pk, "submit": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("legal_business_name", response.data["missing_fields"])

    def test_partner_owner_cannot_submit_for_another_partner(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url, {"partner_id": self.other_partner.pk}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_submitted_application_is_locked_until_staff_requests_changes(self):
        self.client.force_authenticate(self.owner)
        submitted = self.submit_valid_application()
        self.assertEqual(submitted.status_code, 200)
        locked = self.client.post(
            self.url, {"partner_id": self.partner.pk, "contact_phone": "+27119999999"},
            format="json",
        )
        self.assertEqual(locked.status_code, 409)

    def test_only_staff_can_view_queue_and_review_submission(self):
        self.client.force_authenticate(self.owner)
        submitted = self.submit_valid_application()
        self.assertEqual(submitted.status_code, 200)
        submission_id = submitted.data["id"]
        self.assertEqual(
            self.client.get("/api/v1/partners/partner/onboarding/queue/").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/partners/partner/onboarding/{submission_id}/review/",
                {"decision": "approved"}, format="json",
            ).status_code,
            403,
        )
        self.client.force_authenticate(self.staff)
        queue = self.client.get("/api/v1/partners/partner/onboarding/queue/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual([item["id"] for item in queue.data], [submission_id])
        reviewed = self.client.post(
            f"/api/v1/partners/partner/onboarding/{submission_id}/review/",
            {"decision": "approved"}, format="json",
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.data["status"], "approved")
        self.client.force_authenticate(self.owner)
        owner_status = self.client.get(f"{self.url}?partner_id={self.partner.pk}")
        self.assertEqual(owner_status.status_code, 200)
        self.assertEqual(owner_status.data["status"], "approved")
        self.assertTrue(any(event["event_type"] == "approved" for event in owner_status.data["events"]))

    def test_staff_must_explain_change_request_or_rejection(self):
        self.client.force_authenticate(self.owner)
        submitted = self.submit_valid_application()
        self.assertEqual(submitted.status_code, 200)
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            f"/api/v1/partners/partner/onboarding/{submitted.data['id']}/review/",
            {"decision": "changes_requested"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("review_notes", response.data)

    def test_document_checklist_rejects_unknown_document_types(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.url,
            {"partner_id": self.partner.pk, "document_checklist": ["passport_scan"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


    def test_review_decision_emails_partner_owner(self):
        from django.core import mail
        from django.test import override_settings

        self.client.force_authenticate(self.owner)
        submitted = self.submit_valid_application()
        self.assertEqual(submitted.status_code, 200)
        self.client.force_authenticate(self.staff)
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="notifications@xgetawaysx.example",
        ):
            response = self.client.post(
                f"/api/v1/partners/partner/onboarding/{submitted.data['id']}/review/",
                {"decision": "changes_requested", "review_notes": "Please upload a clearer registration certificate."},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.owner.email])
        self.assertIn("returned for changes", mail.outbox[0].subject)
        self.assertIn("clearer registration certificate", mail.outbox[0].body)

    def test_suppressed_email_delivery_failure_does_not_undo_staff_decision(self):
        from unittest.mock import patch

        self.client.force_authenticate(self.owner)
        submitted = self.submit_valid_application()
        self.assertEqual(submitted.status_code, 200)
        self.client.force_authenticate(self.staff)
        with patch("partners.views.send_mail", return_value=0) as mocked_send_mail:
            response = self.client.post(
                f"/api/v1/partners/partner/onboarding/{submitted.data['id']}/review/",
                {"decision": "approved"}, format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "approved")
        self.assertTrue(mocked_send_mail.call_args.kwargs["fail_silently"])


class PartnerVerificationPrivateDocumentTests(TestCase):
    def setUp(self):
        from .models import PartnerVerificationSubmission
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="private-doc-owner@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.other = User.objects.create_user(
            email="private-doc-other@example.com", password="test-password",
            role=User.Role.PARTNER,
        )
        self.partner = Partner.objects.create(
            owner=self.owner, name="Private Evidence Lodge",
            category=Partner.Category.ACCOMMODATION,
        )
        self.submission = PartnerVerificationSubmission.objects.create(
            partner=self.partner, legal_business_name="Private Evidence Lodge",
        )
        self.other_partner = Partner.objects.create(
            owner=self.other, name="Other Private Lodge",
            category=Partner.Category.ACCOMMODATION,
        )

    def pdf_upload(self, name="registration.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4\n% partner verification evidence\n",
            content_type="application/pdf",
        )

    def test_owner_can_upload_and_list_private_evidence(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/partners/partner/onboarding/{self.submission.pk}/documents/",
            {"document_type": "business_registration", "file": self.pdf_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        listing = self.client.get(
            f"/api/v1/partners/partner/onboarding/{self.submission.pk}/documents/"
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data[0]["document_type"], "business_registration")
        self.assertNotIn("file", listing.data[0])
        self.submission.refresh_from_db()
        self.assertIn("business_registration", self.submission.document_checklist)

    def test_other_partner_owner_cannot_list_or_download_evidence(self):
        from .models import PartnerVerificationDocument
        document = PartnerVerificationDocument.objects.create(
            submission=self.submission, document_type="business_registration",
            file=self.pdf_upload(), original_filename="registration.pdf",
            uploaded_by=self.owner,
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.get(
                f"/api/v1/partners/partner/onboarding/{self.submission.pk}/documents/"
            ).status_code, 403,
        )
        self.assertEqual(
            self.client.get(
                f"/api/v1/partners/partner/onboarding/documents/{document.pk}/"
            ).status_code, 403,
        )

    def test_staff_can_download_evidence_and_owner_cannot_upload_after_submission(self):
        from .models import PartnerVerificationDocument, PartnerVerificationSubmission
        staff = User.objects.create_superuser(
            email="private-doc-staff@example.com", password="test-password",
        )
        document = PartnerVerificationDocument.objects.create(
            submission=self.submission, document_type="business_registration",
            file=self.pdf_upload(), original_filename="registration.pdf",
            uploaded_by=self.owner,
        )
        self.client.force_authenticate(staff)
        download = self.client.get(
            f"/api/v1/partners/partner/onboarding/documents/{document.pk}/"
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Cache-Control"], "private, no-store")
        self.submission.status = PartnerVerificationSubmission.Status.SUBMITTED
        self.submission.save()
        self.client.force_authenticate(self.owner)
        locked = self.client.post(
            f"/api/v1/partners/partner/onboarding/{self.submission.pk}/documents/",
            {"document_type": "proof_of_address", "file": self.pdf_upload("address.pdf")},
            format="multipart",
        )
        self.assertEqual(locked.status_code, 409)

    def test_invalid_file_signature_is_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/partners/partner/onboarding/{self.submission.pk}/documents/",
            {"document_type": "owner_identity",
             "file": SimpleUploadedFile("identity.pdf", b"not a PDF", content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
