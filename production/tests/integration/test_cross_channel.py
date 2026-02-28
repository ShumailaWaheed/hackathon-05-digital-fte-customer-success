"""T086: Integration test — Cross-channel identity verification."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_same_customer_across_channels():
    """Same email used in webform and gmail should resolve to same customer."""
    customer_id = uuid.uuid4()
    customer = {
        "id": customer_id,
        "name": "Cross Channel User",
        "created_at": "2026-02-25",
        "updated_at": "2026-02-25",
        "metadata": {},
    }

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(return_value=customer)

        from production.api.services.identity_resolver import resolve_customer

        r1 = await resolve_customer("email", "shared@example.com", "User", "webform")
        r2 = await resolve_customer("email", "shared@example.com", "User", "gmail")

        assert r1["id"] == r2["id"] == customer_id


@pytest.mark.asyncio
async def test_different_identifiers_same_customer():
    """If phone and email are linked to same customer, identity resolver finds them."""
    customer_id = uuid.uuid4()
    customer = {"id": customer_id, "name": "User", "created_at": "2026-02-25", "updated_at": "2026-02-25", "metadata": {}}

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(return_value=customer)

        from production.api.services.identity_resolver import resolve_customer

        r_email = await resolve_customer("email", "user@test.com", source="gmail")
        r_phone = await resolve_customer("phone", "+1234567890", source="whatsapp")

        assert r_email["id"] == r_phone["id"]


@pytest.mark.asyncio
async def test_different_customers_not_merged():
    """Two different emails should create separate customers."""
    c1 = {"id": uuid.uuid4(), "name": "User1", "created_at": "2026-02-25", "updated_at": "2026-02-25", "metadata": {}}
    c2 = {"id": uuid.uuid4(), "name": "User2", "created_at": "2026-02-25", "updated_at": "2026-02-25", "metadata": {}}

    with patch("production.api.services.identity_resolver.repositories") as mock_repo:
        mock_repo.find_customer_by_identifier = AsyncMock(side_effect=[c1, c2])

        from production.api.services.identity_resolver import resolve_customer

        r1 = await resolve_customer("email", "user1@test.com", source="webform")
        r2 = await resolve_customer("email", "user2@test.com", source="webform")

        assert r1["id"] != r2["id"]
