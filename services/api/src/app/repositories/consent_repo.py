from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import Consent
from app.repositories.base import BaseRepository


class ConsentRepository(BaseRepository[Consent]):
    def __init__(self, db: AsyncSession):
        super().__init__(Consent, db)

    async def get_by_user(self, user_id: str) -> Optional[Consent]:
        result = await self.db.execute(select(Consent).where(Consent.user_id == user_id))
        return result.scalar_one_or_none()

    async def has_consent(self, user_id: str, scope: str) -> bool:
        consent = await self.get_by_user(user_id)
        if not consent:
            return False
        if scope == "share_anonymized_soil":
            return consent.share_anonymized_soil
        elif scope == "share_outbreak_telemetry":
            return consent.share_outbreak_telemetry
        elif scope == "participate_in_federated_learning":
            return consent.participate_in_federated_learning
        return False
