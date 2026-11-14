import tempfile
import unittest
from pathlib import Path

from vkus.exchange_marketplace import MarketplaceStore


class MarketplaceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MarketplaceStore(Path(self.temp.name) / "marketplace.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, **overrides):
        data = {
            "kind": "Ищу", "category": "Услуги",
            "title": "Нужен мастер по ремонту",
            "description": "Ищу специалиста для ремонта кухни",
            "city": "Орск", "price": "до 15000 ₽",
            "contact": "@customer", "author": "Покупатель",
        }
        data.update(overrides)
        return data

    def test_create_search_and_read(self):
        listing_id = self.store.create(self.payload())
        self.assertEqual(self.store.get(listing_id)["city"], "Орск")
        self.assertEqual(len(self.store.list_listings(query="кухни")), 1)
        self.assertEqual(len(self.store.list_listings(city="Москва")), 0)

    def test_update_and_status_filter(self):
        listing_id = self.store.create(self.payload())
        self.store.update(listing_id, self.payload(kind="Предлагаю", title="Ремонт под ключ"))
        self.store.set_status(listing_id, "Завершено")
        self.assertEqual(self.store.get(listing_id)["kind"], "Предлагаю")
        self.assertEqual(len(self.store.list_listings()), 0)
        self.assertEqual(len(self.store.list_listings(status="Все статусы")), 1)

    def test_delete_and_validation(self):
        listing_id = self.store.create(self.payload())
        self.store.delete(listing_id)
        self.assertIsNone(self.store.get(listing_id))
        with self.assertRaises(ValueError):
            self.store.create(self.payload(title=""))

    def test_injection_like_search_is_parameterized(self):
        self.store.create(self.payload())
        self.assertEqual(self.store.list_listings(query="' OR 1=1 --"), [])


if __name__ == "__main__":
    unittest.main()
