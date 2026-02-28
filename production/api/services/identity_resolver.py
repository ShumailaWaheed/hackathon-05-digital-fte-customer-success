"""Customer identity resolution service.

T050: Centralized resolve_customer() function for cross-channel identity.
Looks up customer_identifiers table, returns existing customer or creates
new customer + links identifier. Per FR-011, FR-012.
"""

from __future__ import annotations

import logging

from production.database import repositories

logger = logging.getLogger(__name__)


async def resolve_customer(
    identifier_type: str,
    identifier_value: str,
    name: str | None = None,
    source: str = "unknown",
) -> dict:
    """Resolve a customer by identifier, creating if needed.

    Args:
        identifier_type: "email", "phone", or "form_session".
        identifier_value: The actual email/phone/session value.
        name: Display name (used when creating a new customer).
        source: Channel source for metadata (e.g., "gmail", "whatsapp", "webform").

    Returns:
        Customer dict with id, name, created_at, etc.
    """
    # Try to find existing customer
    customer = await repositories.find_customer_by_identifier(
        identifier_type, identifier_value
    )
    if customer:
        logger.debug(
            "Customer resolved: id=%s type=%s value=%s",
            customer["id"], identifier_type, identifier_value,
        )
        return customer

    # Create new customer
    display_name = name or identifier_value
    customer = await repositories.create_customer(
        name=display_name,
        metadata={"source": source, "initial_identifier": identifier_value},
    )
    await repositories.link_identifier(
        customer_id=customer["id"],
        identifier_type=identifier_type,
        identifier_value=identifier_value,
    )

    logger.info(
        "New customer created: id=%s type=%s value=%s source=%s",
        customer["id"], identifier_type, identifier_value, source,
    )
    return customer
