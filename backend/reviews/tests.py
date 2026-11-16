from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from events.models import Event, EventCategory
from reviews.models import Review


class ReviewAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.test", password="test-pass-123", role="ADMIN"
        )
        self.organizer = User.objects.create_user(
            username="organizer", email="organizer@example.test", password="test-pass-123", role="ORGANIZER"
        )
        self.customer = User.objects.create_user(
            username="customer", email="customer@example.test", password="test-pass-123", role="CUSTOMER"
        )
        self.other_customer = User.objects.create_user(
            username="other", email="other@example.test", password="test-pass-123", role="CUSTOMER"
        )
        category = EventCategory.objects.create(name="Review Test Category")
        event_fields = {
            "description": "Review test event",
            "category": category,
            "organizer": self.organizer,
            "venue": "Test venue",
            "city": "Test city",
            "event_date": timezone.localdate() + timedelta(days=30),
            "start_time": "14:00",
            "end_time": "18:00",
            "ticket_price": 25,
            "total_tickets": 20,
            "available_tickets": 20,
        }
        self.approved_event = Event.objects.create(
            title="Approved Review Event", status=Event.Status.APPROVED, **event_fields
        )
        self.pending_event = Event.objects.create(
            title="Pending Review Event", status=Event.Status.PENDING, **event_fields
        )
        self.url = reverse("review-list")

    def test_customer_can_review_approved_event_and_user_is_server_assigned(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url,
            {"event": self.approved_event.id, "rating": 5, "comment": "Great", "user": self.other_customer.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.customer.id)
        self.assertEqual(Review.objects.get(pk=response.data["id"]).user, self.customer)

    def test_anonymous_cannot_create_review(self):
        response = self.client.post(
            self.url, {"event": self.approved_event.id, "rating": 4}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_customer_cannot_create_review(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.post(
            self.url, {"event": self.approved_event.id, "rating": 4}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_review_of_non_approved_event_is_rejected(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url, {"event": self.pending_event.id, "rating": 4}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("event", response.data)

    def test_duplicate_review_returns_validation_error(self):
        Review.objects.create(user=self.customer, event=self.approved_event, rating=4)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url, {"event": self.approved_event.id, "rating": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("event", response.data)

    def test_review_list_can_be_filtered_by_event(self):
        own = Review.objects.create(user=self.customer, event=self.approved_event, rating=4)
        Review.objects.create(user=self.other_customer, event=self.pending_event, rating=2)
        response = self.client.get(self.url, {"event": self.approved_event.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], own.id)

    def test_invalid_rating_is_rejected(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url, {"event": self.approved_event.id, "rating": 6}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_list_and_detail_are_public(self):
        review = Review.objects.create(user=self.customer, event=self.approved_event, rating=5)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(reverse("review-detail", args=[review.id])).status_code,
            status.HTTP_200_OK,
        )

    def test_only_review_owner_can_update_or_delete(self):
        review = Review.objects.create(user=self.customer, event=self.approved_event, rating=3)
        self.client.force_authenticate(self.other_customer)
        detail_url = reverse("review-detail", args=[review.id])
        self.assertEqual(
            self.client.patch(detail_url, {"rating": 2}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_review(self):
        review = Review.objects.create(user=self.customer, event=self.approved_event, rating=3)
        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            reverse("review-detail", args=[review.id]), {"rating": 4}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
