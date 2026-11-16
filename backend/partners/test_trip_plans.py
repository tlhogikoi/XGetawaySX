from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import Partner, TripPlan


class CustomerTripPlanApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="traveller@example.com", password="Strong-passphrase-2026!"
        )
        self.other_customer = User.objects.create_user(
            email="other@example.com", password="Strong-passphrase-2026!"
        )
        self.partner_owner = User.objects.create_user(
            email="host@example.com", password="Strong-passphrase-2026!"
        )
        self.approved_partner = Partner.objects.create(
            owner=self.partner_owner,
            name="Mountain Escape",
            slug="mountain-escape",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.APPROVED,
            enquiry_status=Partner.ApprovalStatus.APPROVED,
        )
        self.pending_partner = Partner.objects.create(
            owner=self.partner_owner,
            name="Pending Retreat",
            slug="pending-retreat",
            category=Partner.Category.ACCOMMODATION,
            gallery_status=Partner.ApprovalStatus.PENDING,
            enquiry_status=Partner.ApprovalStatus.PENDING,
        )
        self.client.force_authenticate(user=self.customer)

    def test_customer_can_create_and_update_private_plan_notes_and_dates(self):
        created = self.client.post(
            "/api/v1/partners/trips/",
            {"title": "Drakensberg weekend"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        plan_id = created.data["id"]

        updated = self.client.patch(
            f"/api/v1/partners/trips/{plan_id}/",
            {
                "notes": "Anniversary weekend; prefer a quiet room.",
                "start_date": "2027-04-02",
                "end_date": "2027-04-05",
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["notes"], "Anniversary weekend; prefer a quiet room.")
        self.assertEqual(updated.data["start_date"], "2027-04-02")
        self.assertEqual(updated.data["end_date"], "2027-04-05")

    def test_customer_cannot_read_or_edit_another_customers_plan(self):
        other_plan = TripPlan.objects.create(owner=self.other_customer, title="Private trip")
        response = self.client.get(f"/api/v1/partners/trips/{other_plan.pk}/")
        self.assertEqual(response.status_code, 404)
        update = self.client.patch(
            f"/api/v1/partners/trips/{other_plan.pk}/",
            {"notes": "Attempted access"},
            format="json",
        )
        self.assertEqual(update.status_code, 404)
        self.assertEqual(other_plan.notes, "")

    def test_only_approved_partners_can_be_added_to_itinerary(self):
        plan = TripPlan.objects.create(owner=self.customer, title="Coastal break")
        added = self.client.post(
            f"/api/v1/partners/trips/{plan.pk}/items/",
            {"partner_id": self.approved_partner.pk},
            format="json",
        )
        self.assertEqual(added.status_code, 201)
        self.assertEqual(len(added.data["items"]), 1)
        self.assertEqual(added.data["items"][0]["partner"]["slug"], "mountain-escape")

        rejected = self.client.post(
            f"/api/v1/partners/trips/{plan.pk}/items/",
            {"partner_id": self.pending_partner.pk},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)

    def test_end_date_cannot_precede_start_date(self):
        plan = TripPlan.objects.create(owner=self.customer, title="Date validation")
        response = self.client.patch(
            f"/api/v1/partners/trips/{plan.pk}/",
            {"start_date": "2027-05-10", "end_date": "2027-05-08"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        plan.refresh_from_db()
        self.assertIsNone(plan.start_date)
        self.assertIsNone(plan.end_date)
