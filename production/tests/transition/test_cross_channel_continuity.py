"""T081: Test cross-channel customer identity continuity.

Same email across webform and gmail should resolve to same customer.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_same_email_resolves_same_customer():
    """Customer with same email across channels should be the same."""
    customer = {
        "id": uuid.uuid4(),
        "name": "Test User",
        "created_at": "2026-02-25",
        "updated_at": "2026-02-25",
        "metadata": {},
    }

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(return_value=customer)

        from production.api.services.identity_resolver import resolve_customer

        # Webform resolution
        result1 = await resolve_customer("email", "user@example.com", "User", "webform")
        assert result1["id"] == customer["id"]

        # Gmail resolution — same email
        result2 = await resolve_customer("email", "user@example.com", "User", "gmail")
        assert result2["id"] == customer["id"]
        assert result1["id"] == result2["id"]


@pytest.mark.asyncio
async def test_new_customer_created_when_not_found():
    """Unknown identifier should create a new customer."""
    new_customer = {
        "id": uuid.uuid4(),
        "name": "New User",
        "created_at": "2026-02-25",
        "updated_at": "2026-02-25",
        "metadata": {},
    }

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(return_value=None)
        mock_repo.create_customer = AsyncMock(return_value=new_customer)
        mock_repo.link_identifier = AsyncMock()

        from production.api.services.identity_resolver import resolve_customer

        result = await resolve_customer("email", "new@example.com", "New User", "webform")
        assert result["id"] == new_customer["id"]
        mock_repo.create_customer.assert_called_once()
        mock_repo.link_identifier.assert_called_once()


@pytest.mark.asyncio
async def test_phone_identifier_resolves():
    """WhatsApp phone identifier should resolve correctly."""
    customer = {"id": uuid.uuid4(), "name": "+1234567890", "created_at": "2026-02-25", "updated_at": "2026-02-25", "metadata": {}}

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(return_value=customer)

        from production.api.services.identity_resolver import resolve_customer
        result = await resolve_customer("phone", "+1234567890", source="whatsapp")
        assert result["id"] == customer["id"]
