"""Supabase client for Vkus' first-party marketplace.

Uses Supabase Auth + the PostgREST Data API over the Python standard library.
Only the publishable key belongs in the desktop client; service-role keys are
never accepted or stored here. Row access is enforced by database RLS.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_SUPABASE_URL = "https://tynutsraotlptyznbpfc.supabase.co"
DEFAULT_PUBLISHABLE_KEY = "sb_publishable_srOxC-k9uOqtl51SWYz8dg_AZ7Pd6Do"


class CloudMarketplaceError(RuntimeError):
    """A safe, user-displayable error returned by the cloud service."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str
    user: dict[str, Any]
    expires_at: Optional[int] = None


class SupabaseMarketplaceClient:
    """Small REST client with password auth and user-scoped marketplace access."""

    def __init__(self, url: str | None = None, publishable_key: str | None = None,
                 timeout: int = 15):
        self.url = (url or os.getenv("VKUS_SUPABASE_URL") or DEFAULT_SUPABASE_URL).rstrip("/")
        self.publishable_key = (
            publishable_key or os.getenv("VKUS_SUPABASE_PUBLISHABLE_KEY")
            or DEFAULT_PUBLISHABLE_KEY
        )
        self.timeout = timeout
        self.session: AuthSession | None = None
        self.session_persistence_available = False
        self._restore_secure_session()
        if not self.url.startswith("https://"):
            raise ValueError("Для облачной биржи требуется HTTPS URL Supabase.")
        if not self.publishable_key.startswith(("sb_publishable_", "eyJ")):
            raise ValueError("Укажите публичный ключ Supabase (publishable key).")

    @property
    def is_authenticated(self) -> bool:
        return bool(self.session and self.session.access_token)

    def _request(self, method: str, path: str, payload: dict | None = None,
                 *, authenticated: bool = False, query: dict | None = None,
                 prefer: str | None = None):
        if authenticated:
            self._ensure_fresh_session()
        url = self.url + path
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        headers = {
            "apikey": self.publishable_key,
            "Accept": "application/json",
        }
        if authenticated:
            if not self.session:
                raise CloudMarketplaceError("Сначала войдите в аккаунт Vkus.")
            headers["Authorization"] = "Bearer " + self.session.access_token
        else:
            headers["Authorization"] = "Bearer " + self.publishable_key
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = prefer or "return=representation"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8"))
                message = data.get("msg") or data.get("message") or data.get("error_description") or data.get("error")
            except Exception:
                message = None
            if exc.code in (401, 403):
                message = message or "Доступ отклонён. Проверьте вход и права доступа."
            elif exc.code == 429:
                message = "Слишком много запросов. Подождите немного и повторите."
            raise CloudMarketplaceError(message or f"Ошибка облачной биржи (HTTP {exc.code}).", status_code=exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise CloudMarketplaceError(
                "Не удалось подключиться к облачной бирже. Проверьте интернет-соединение."
            ) from None
        except json.JSONDecodeError:
            raise CloudMarketplaceError("Облачная биржа вернула некорректный ответ.") from None

    def sign_up(self, email: str, password: str) -> dict:
        email, password = email.strip(), password
        if not email or "@" not in email:
            raise ValueError("Введите корректный email.")
        if len(password) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов.")
        result = self._request("POST", "/auth/v1/signup",
                               {"email": email, "password": password})
        self._accept_auth_result(result)
        return result or {}

    def sign_in(self, email: str, password: str) -> dict:
        if not email.strip() or not password:
            raise ValueError("Введите email и пароль.")
        result = self._request(
            "POST", "/auth/v1/token?grant_type=password",
            {"email": email.strip(), "password": password},
        )
        self._accept_auth_result(result)
        if not self.session:
            raise CloudMarketplaceError(
                "Аккаунт создан. Подтвердите email по ссылке из письма, затем войдите."
            )
        return result

    def _accept_auth_result(self, result: dict | None, *, persist: bool = True):
        if not result or not result.get("access_token") or not result.get("refresh_token"):
            self.session = None
            return
        self.session = AuthSession(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user=result.get("user") or {},
            expires_at=result.get("expires_at") or (int(time.time()) + int(result.get("expires_in", 3600))),
        )
        if persist:
            self.session_persistence_available = self._save_secure_session()

    def _keyring(self):
        try:
            import keyring
            backend = keyring.get_keyring()
            if getattr(backend, "priority", 0) <= 0:
                return None
            return keyring
        except Exception:
            return None

    def _secure_store_account(self) -> str:
        return self.url

    def _save_secure_session(self) -> bool:
        if not self.session:
            return False
        keyring = self._keyring()
        if keyring is None:
            return False
        try:
            payload = {"access_token": self.session.access_token,
                       "refresh_token": self.session.refresh_token,
                       "user": self.session.user,
                       "expires_at": self.session.expires_at}
            keyring.set_password("Vkus.Supabase.Marketplace", self._secure_store_account(),
                                 json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:
            return False

    def _delete_secure_session(self):
        keyring = self._keyring()
        if keyring is None:
            return
        try:
            keyring.delete_password("Vkus.Supabase.Marketplace", self._secure_store_account())
        except Exception:
            pass

    def _restore_secure_session(self):
        keyring = self._keyring()
        if keyring is None:
            self.session_persistence_available = False
            return
        try:
            raw = keyring.get_password("Vkus.Supabase.Marketplace", self._secure_store_account())
            if not raw:
                self.session_persistence_available = True
                return
            saved = json.loads(raw)
            if not saved.get("refresh_token") or not saved.get("user", {}).get("id"):
                self._delete_secure_session()
                return
            self.session = AuthSession(
                access_token=str(saved.get("access_token") or ""),
                refresh_token=str(saved["refresh_token"]),
                user=saved["user"], expires_at=saved.get("expires_at"),
            )
            # Rotate the refresh token immediately; never trust an old access token.
            self.refresh_session()
        except CloudMarketplaceError as exc:
            # A temporary network/server failure must not destroy a valid refresh token.
            if exc.status_code in (400, 401, 403):
                self.session = None
                self._delete_secure_session()
                self.session_persistence_available = False
            else:
                self.session_persistence_available = True
        except Exception:
            self.session = None
            self._delete_secure_session()
            self.session_persistence_available = False

    def _ensure_fresh_session(self):
        if not self.session:
            raise CloudMarketplaceError("Сначала войдите в аккаунт Vkus.")
        if getattr(self.session, "expires_at", None) and self.session.expires_at <= int(time.time()) + 60:
            try:
                self.refresh_session()
            except CloudMarketplaceError as exc:
                if exc.status_code in (400, 401, 403):
                    self.session = None
                    self._delete_secure_session()
                    raise CloudMarketplaceError("Сессия истекла или отозвана. Войдите снова.") from None
                raise

    def refresh_session(self):
        if not self.session:
            raise CloudMarketplaceError("Нет активной сессии.")
        result = self._request(
            "POST",
            "/auth/v1/token?grant_type=refresh_token",
            {"refresh_token": self.session.refresh_token},
            authenticated=False,
        )
        self._accept_auth_result(result)
        if not self.session:
            raise CloudMarketplaceError("Сессия истекла. Войдите снова.")
        return self.session

    def sign_out(self):
        if self.session:
            try:
                self._request("POST", "/auth/v1/logout", authenticated=True)
            finally:
                self.session = None
                self._delete_secure_session()
                self.session_persistence_available = bool(self._keyring())

    def list_listings(self, *, search: str = "", kind: str = "Все типы",
                      category: str = "Все категории", city: str = "",
                      limit: int = 50, offset: int = 0) -> list[dict]:
        query: dict[str, Any] = {
            "select": "id,owner_id,kind,category,title,description,city,price,currency,contact,status,created_at,updated_at",
            "status": "eq.Активно",
            "order": "created_at.desc",
            "limit": max(1, min(int(limit), 100)),
            "offset": max(0, int(offset)),
        }
        if kind != "Все типы":
            query["kind"] = "eq." + kind
        if category != "Все категории":
            query["category"] = "eq." + category
        if city.strip():
            query["city"] = "ilike.*" + city.strip() + "*"
        if search.strip():
            safe = search.strip().replace("%", r"\%").replace("_", r"\_").replace("*", r"\*")
            query["or"] = (
                f"(title.ilike.*{safe}*,description.ilike.*{safe}*,"
                f"city.ilike.*{safe}*,category.ilike.*{safe}*)"
            )
        result = self._request("GET", "/rest/v1/marketplace_listings",
                               authenticated=self.is_authenticated, query=query)
        return result or []

    def get_my_profile(self) -> dict:
        self._require_auth()
        rows = self._request(
            "GET", "/rest/v1/marketplace_profiles", authenticated=True,
            query={"select": "id,display_name,city,avatar_url",
                   "id": "eq." + str(self.session.user["id"]), "limit": 1},
        )
        return rows[0] if rows else {}

    def save_my_profile(self, display_name: str, city: str = "") -> dict:
        self._require_auth()
        display_name = display_name.strip()
        city = city.strip()
        if not display_name or len(display_name) > 80:
            raise ValueError("Имя профиля должно содержать от 1 до 80 символов.")
        if len(city) > 80:
            raise ValueError("Название города не должно превышать 80 символов.")
        rows = self._request(
            "POST", "/rest/v1/marketplace_profiles",
            {"id": self.session.user["id"], "display_name": display_name, "city": city or None},
            authenticated=True, query={"on_conflict": "id"},
            prefer="resolution=merge-duplicates,return=representation",
        )
        return rows[0] if rows else {"display_name": display_name, "city": city}

    def create_listing(self, payload: dict) -> dict:
        self._require_auth()
        data = self._normalize_listing(payload)
        result = self._request("POST", "/rest/v1/marketplace_listings",
                               data, authenticated=True)
        return (result or [{}])[0]

    def update_listing(self, listing_id: str, payload: dict) -> dict:
        self._require_auth()
        data = self._normalize_listing(payload)
        result = self._request(
            "PATCH", "/rest/v1/marketplace_listings",
            data, authenticated=True,
            query={"id": "eq." + str(listing_id)},
        )
        if not result:
            raise CloudMarketplaceError("Объявление не найдено или нет прав на изменение.")
        return result[0]

    def delete_listing(self, listing_id: str):
        self._require_auth()
        self._request("DELETE", "/rest/v1/marketplace_listings",
                      authenticated=True, query={"id": "eq." + str(listing_id)})

    def respond_to_listing(self, listing_id: str, message: str) -> dict:
        self._require_auth()
        message = message.strip()
        if not message or len(message) > 2000:
            raise ValueError("Сообщение должно содержать от 1 до 2000 символов.")
        result = self._request(
            "POST", "/rest/v1/marketplace_responses",
            {"listing_id": str(listing_id), "message": message},
            authenticated=True,
        )
        return (result or [{}])[0]

    def list_my_responses(self, *, limit: int = 50, offset: int = 0) -> list[dict]:
        self._require_auth()
        result = self._request(
            "GET", "/rest/v1/marketplace_responses",
            authenticated=True,
            query={
                "select": "id,listing_id,sender_id,message,status,created_at",
                "sender_id": "eq." + str(self.session.user["id"]),
                "order": "created_at.desc",
                "limit": max(1, min(int(limit), 100)),
                "offset": max(0, int(offset)),
            },
        )
        return result or []

    def list_incoming_responses(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        """Return responses to listings owned by the signed-in user (RLS enforced)."""
        self._require_auth()
        result = self._request(
            "GET", "/rest/v1/marketplace_responses",
            authenticated=True,
            query={
                "select": "id,listing_id,sender_id,message,status,created_at,listing:marketplace_listings!inner(id,title,owner_id)",
                "listing.owner_id": "eq." + str(self.session.user["id"]),
                "order": "created_at.desc",
                "limit": max(1, min(int(limit), 100)),
                "offset": max(0, int(offset)),
            },
        )
        return result or []

    def update_response_status(self, response_id: str, status: str) -> dict:
        """Change a response status; database RLS restricts this to listing owners."""
        self._require_auth()
        if status not in ("Просмотрен", "Принят", "Отклонён"):
            raise ValueError("Недопустимый статус отклика.")
        result = self._request(
            "PATCH", "/rest/v1/marketplace_responses",
            {"status": status}, authenticated=True,
            query={"id": "eq." + str(response_id)},
        )
        if not result:
            raise CloudMarketplaceError("Отклик не найден или нет прав на изменение.")
        return result[0]

    def _require_auth(self):
        if not self.is_authenticated:
            raise CloudMarketplaceError("Для этого действия войдите в аккаунт Vkus.")

    @staticmethod
    def _normalize_listing(payload: dict) -> dict:
        required = ("kind", "category", "title", "description", "city")
        for key in required:
            if not str(payload.get(key, "")).strip():
                raise ValueError("Заполните тип, категорию, заголовок, описание и город.")
        if payload["kind"] not in ("Ищу", "Предлагаю"):
            raise ValueError("Неизвестный тип объявления.")
        if payload["category"] not in (
            "Товары", "Услуги", "Работа", "Подряд и задачи",
            "Аренда", "Покупка", "Продажа", "Другое",
        ):
            raise ValueError("Неизвестная категория.")
        title = payload["title"].strip()
        description = payload["description"].strip()
        city = payload["city"].strip()
        if len(title) > 120 or len(description) > 5000 or len(city) > 80:
            raise ValueError("Превышена допустимая длина заголовка, описания или города.")
        raw_price = payload.get("price")
        if raw_price not in (None, ""):
            try:
                raw_price = float(str(raw_price).replace(",", "."))
                if raw_price < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Цена или бюджет должны быть неотрицательным числом.") from None
        else:
            raw_price = None
        currency = payload.get("currency") or "RUB"
        if currency not in ("RUB", "EUR", "USD"):
            raise ValueError("Выберите поддерживаемую валюту.")
        return {
            "kind": payload["kind"],
            "category": payload["category"],
            "title": title,
            "description": description,
            "city": city,
            "price": raw_price,
            "currency": currency,
            "contact": (payload.get("contact") or "").strip(),
        }
