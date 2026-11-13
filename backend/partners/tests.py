from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

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
            end_date=self.start + timezone.timedelta(days=2), guests=2,
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

