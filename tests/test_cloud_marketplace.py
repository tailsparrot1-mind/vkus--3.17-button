import unittest
from unittest.mock import patch

from vkus.cloud_marketplace import CloudMarketplaceError, SupabaseMarketplaceClient


class CloudMarketplaceClientTests(unittest.TestCase):
    def setUp(self):
        self.client = SupabaseMarketplaceClient(
            url="https://example.supabase.co", publishable_key="sb_publishable_test"
        )

    def test_auth_session_is_created(self):
        response = {"access_token": "access", "refresh_token": "refresh",
                    "user": {"id": "user-1", "email": "person@example.com"}}
        with patch.object(self.client, "_request", return_value=response) as request:
            self.client.sign_in("person@example.com", "long-password")
        self.assertTrue(self.client.is_authenticated)
        self.assertEqual(self.client.session.user["id"], "user-1")
        self.assertIn("grant_type=password", request.call_args.args[1])

    def test_signup_validation(self):
        with self.assertRaises(ValueError):
            self.client.sign_up("not-an-email", "long-password")
        with self.assertRaises(ValueError):
            self.client.sign_up("person@example.com", "short")

    def test_signup_email_confirmation(self):
        with patch.object(self.client, "_request", return_value={"user": {"id": "u"}}):
            result = self.client.sign_up("person@example.com", "long-password")
        self.assertIn("user", result)
        self.assertFalse(self.client.is_authenticated)

    def test_create_listing_requires_auth_and_maps_fields(self):
        payload = {"kind": "Ищу", "category": "Товары", "title": "Куплю цветы",
                   "description": "Букет к празднику", "city": "Орск",
                   "price": "3000", "contact": "@buyer"}
        with self.assertRaises(CloudMarketplaceError):
            self.client.create_listing(payload)
        self.client.session = type("Session", (), {
            "access_token": "token", "refresh_token": "refresh",
            "user": {"id": "u1"},
        })()
        with patch.object(self.client, "_request", return_value=[{"id": "listing-1"}]) as request:
            result = self.client.create_listing(payload)
        self.assertEqual(result["id"], "listing-1")
        self.assertEqual(request.call_args.args[1], "/rest/v1/marketplace_listings")
        self.assertEqual(request.call_args.args[2]["currency"], "RUB")

    def test_public_search_filters_and_pagination(self):
        with patch.object(self.client, "_request", return_value=[]) as request:
            self.client.list_listings(search="цветы", kind="Ищу", city="Орск", limit=20, offset=40)
        query = request.call_args.kwargs["query"]
        self.assertEqual(query["kind"], "eq.Ищу")
        self.assertEqual(query["city"], "ilike.*Орск*")
        self.assertEqual(query["limit"], 20)
        self.assertEqual(query["offset"], 40)
        self.assertIn("цветы", query["or"])

    def test_invalid_listing_is_rejected(self):
        with self.assertRaises(ValueError):
            self.client._normalize_listing({"kind": "Неверно"})


if __name__ == "__main__":
    unittest.main()
