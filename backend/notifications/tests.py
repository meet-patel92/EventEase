from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from drf_spectacular.generators import SchemaGenerator
from datetime import date, time, timedelta

from accounts.models import User
from bookings.models import Booking
from events.models import Event
from notifications.models import Notification


class NotificationAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.test", password="test-pass-123", role="ADMIN"
        )
        self.customer = User.objects.create_user(
            username="customer", email="customer@example.test", password="test-pass-123", role="CUSTOMER"
        )
        self.other_customer = User.objects.create_user(
            username="other", email="other@example.test", password="test-pass-123", role="CUSTOMER"
        )
        self.own_notification = Notification.objects.create(
            user=self.customer, title="Booking update", message="Your booking is confirmed."
        )
        self.other_notification = Notification.objects.create(
            user=self.other_customer, title="Private update", message="Private message."
        )
        self.admin_notification = Notification.objects.create(
            user=self.admin, title="Admin update", message="Private admin message."
        )
        self.url = reverse("notification-list")

    def test_openapi_lists_notification_operations_under_notifications_tag(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        paths = schema["paths"]
        expected = {
            "/api/v1/notifications/": "get",
            "/api/v1/notifications/unread-count/": "get",
            "/api/v1/notifications/{id}/mark-read/": "patch",
            "/api/v1/notifications/mark-all-read/": "patch",
        }
        for path, method in expected.items():
            with self.subTest(path=path, method=method):
                operation = paths[path][method]
                self.assertIn("Notifications", operation["tags"])
        self.assertEqual(
            schema["paths"]["/api/v1/notifications/unread-count/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/UnreadCount",
        )

    def test_anonymous_user_cannot_list_notifications(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.patch(reverse("notification-mark-all-read")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.patch(reverse("notification-mark-read", args=[self.own_notification.id])).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_customer_sees_only_own_notifications(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.own_notification.id)
        self.assertFalse(response.data["results"][0]["is_read"])

    def test_internal_demo_notifications_are_not_public_or_counted(self):
        Notification.objects.create(
            user=self.customer,
            title="[DEMO] 01 Event reminder",
            message="[DEMO DATA] Internal sample notice.",
        )
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).data["unread_count"], 1
        )

    def test_customer_cannot_retrieve_another_users_notification(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("notification-detail", args=[self.other_notification.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_only_own_notifications(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.admin_notification.id)

    def test_notification_read_status_and_unread_count(self):
        self.client.force_authenticate(self.customer)
        self.assertFalse(self.own_notification.is_read)
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).data["unread_count"], 1
        )
        response = self.client.patch(
            reverse("notification-mark-read", args=[self.own_notification.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).data["unread_count"], 0
        )

    def test_user_cannot_mark_another_users_notification_as_read(self):
        self.client.force_authenticate(self.customer)
        response = self.client.patch(
            reverse("notification-mark-read", args=[self.other_notification.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_mark_all_read_is_scoped_to_the_authenticated_user(self):
        own_second = Notification.objects.create(
            user=self.customer, title="Second update", message="Another private message."
        )
        self.client.force_authenticate(self.customer)
        response = self.client.patch(reverse("notification-mark-all-read"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"updated": 2, "unread_count": 0})
        self.own_notification.refresh_from_db()
        own_second.refresh_from_db()
        self.other_notification.refresh_from_db()
        self.admin_notification.refresh_from_db()
        self.assertTrue(self.own_notification.is_read)
        self.assertTrue(own_second.is_read)
        self.assertFalse(self.other_notification.is_read)
        self.assertFalse(self.admin_notification.is_read)

    def test_legacy_post_action_is_still_supported(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("notification-mark-read", args=[self.own_notification.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_read"])

    def test_notifications_are_read_only(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.post(self.url, {"title": "Injected"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        detail_url = reverse("notification-detail", args=[self.own_notification.id])
        self.assertEqual(
            self.client.patch(detail_url, {"title": "Changed"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AdminSendNotificationAPITest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="send-admin", email="send-admin@example.test",
            password="test-pass-123", role=User.Role.ADMIN,
        )
        self.customer = User.objects.create_user(
            username="send-customer", email="send-customer@example.test",
            password="test-pass-123", role=User.Role.CUSTOMER,
        )
        self.organizer = User.objects.create_user(
            username="send-organizer", email="send-organizer@example.test",
            password="test-pass-123", role=User.Role.ORGANIZER,
        )
        self.other_customer = User.objects.create_user(
            username="send-other", email="send-other@example.test",
            password="test-pass-123", role=User.Role.CUSTOMER,
        )
        self.event = Event.objects.create(
            title="Customer update event",
            description="Approved event for notification recipient tests.",
            organizer=self.admin,
            venue="Community Hall",
            city="Bengaluru",
            event_date=date.today() + timedelta(days=10),
            start_time=time(18, 0),
            end_time=time(20, 0),
            status=Event.Status.APPROVED,
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            event=self.event,
            quantity=1,
            unit_price="25.00",
            total_amount="25.00",
            status=Booking.Status.PENDING,
        )
        self.url = reverse("notification-send")
        self.payload = {
            "title": "Schedule update",
            "message": "Doors open at 6 PM.",
            "type": Notification.Type.PUSH,
            "recipient_scope": "ALL_CUSTOMERS",
        }

    def test_admin_can_notify_all_active_customers_in_app_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipient_count"], 2)
        self.assertEqual(response.data["delivery"], "IN_APP_ONLY")
        notifications = Notification.objects.filter(title="Schedule update")
        self.assertEqual(notifications.count(), 2)
        self.assertSetEqual(
            set(notifications.values_list("user_id", flat=True)),
            {self.customer.id, self.other_customer.id},
        )
        self.assertTrue(all(item.status == Notification.Status.PENDING for item in notifications))
        self.assertTrue(all(item.sent_at is None for item in notifications))

    def test_admin_can_send_to_one_selected_customer(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url,
            {**self.payload, "recipient_scope": "CUSTOMER", "customer": self.other_customer.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipient_count"], 1)
        self.assertQuerySetEqual(
            Notification.objects.filter(title="Schedule update").values_list("user_id", flat=True),
            [self.other_customer.id],
        )

    def test_sent_notification_appears_in_customer_inbox_and_unread_count(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            self.url,
            {**self.payload, "recipient_scope": "CUSTOMER", "customer": self.customer.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.customer)
        inbox = self.client.get(reverse("notification-list"))
        self.assertEqual(inbox.status_code, status.HTTP_200_OK)
        received = next(
            item for item in inbox.data["results"] if item["title"] == "Schedule update"
        )
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).data["unread_count"], 1
        )
        marked = self.client.patch(
            reverse("notification-mark-read", args=[received["id"]])
        )
        self.assertEqual(marked.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(reverse("notification-unread-count")).data["unread_count"], 0
        )

    def test_admin_can_send_only_to_customers_with_active_bookings_for_event(self):
        Booking.objects.create(
            customer=self.other_customer,
            event=self.event,
            quantity=2,
            unit_price="25.00",
            total_amount="50.00",
            status=Booking.Status.CONFIRMED,
        )
        Booking.objects.create(
            customer=self.other_customer,
            event=self.event,
            quantity=1,
            unit_price="25.00",
            total_amount="25.00",
            status=Booking.Status.CANCELLED,
        )
        booking_count = Booking.objects.count()
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url,
            {**self.payload, "recipient_scope": "EVENT_CUSTOMERS", "event": self.event.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipient_count"], 2)
        self.assertEqual(Booking.objects.count(), booking_count)
        self.assertSetEqual(
            set(Notification.objects.filter(title="Schedule update").values_list("user_id", flat=True)),
            {self.customer.id, self.other_customer.id},
        )

    def test_non_admin_cannot_send_or_fetch_recipient_options(self):
        for user in (self.customer, self.organizer):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                self.assertEqual(
                    self.client.post(self.url, self.payload, format="json").status_code,
                    status.HTTP_403_FORBIDDEN,
                )
                self.assertEqual(
                    self.client.get(reverse("notification-send-options")).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_invalid_recipient_selection_and_empty_event_are_rejected(self):
        self.client.force_authenticate(self.admin)
        missing_customer = self.client.post(
            self.url,
            {**self.payload, "recipient_scope": "CUSTOMER"},
            format="json",
        )
        self.assertEqual(missing_customer.status_code, status.HTTP_400_BAD_REQUEST)
        empty_event = Event.objects.create(
            title="No bookings event",
            description="No booking records.",
            organizer=self.admin,
            venue="Community Hall",
            city="Bengaluru",
            event_date=date.today() + timedelta(days=20),
            start_time=time(18, 0),
            end_time=time(20, 0),
            status=Event.Status.APPROVED,
        )
        no_recipients = self.client.post(
            self.url,
            {**self.payload, "recipient_scope": "EVENT_CUSTOMERS", "event": empty_event.id},
            format="json",
        )
        self.assertEqual(no_recipients.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Notification.objects.count(), 0)

    def test_admin_options_include_customers_and_booked_events(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("notification-send-options"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["customers"]), 2)
        self.assertEqual(response.data["events"][0]["id"], self.event.id)
        self.assertEqual(response.data["events"][0]["recipient_count"], 1)
