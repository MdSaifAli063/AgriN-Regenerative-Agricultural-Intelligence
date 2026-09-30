"""
KrishiNet-BRICS - Data Retention & "Delete My Data" (Right to be Forgotten) Procedure.
Implements data sovereignty and privacy compliance (DPDP, GDPR, LGPD):
1. End-to-end user data erasure across DB, object storage, and cache.
2. Scheduled retention purges for inbound/outbound messages (default 30 days).
3. Temporary media & transient telemetry cleanup.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
from app.models.advisory import Advisory
from app.models.audit import AuditLog, Notification
from app.models.disease import DiseaseDetection
from app.models.farm import Farm, Field
from app.models.messaging import InboundMessage, MessageSession, OutboundMessage
from app.models.user import Consent, User
from app.services.storage import storage_service
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("krishinet.privacy.retention")


class DataRetentionManager:
    """Manages data retention policies and executes user deletion requests."""

    @classmethod
    async def purge_expired_messages(
        cls,
        db: AsyncSession,
        retention_days: int = 30,
    ) -> Dict[str, int]:
        """
        Purges inbound and outbound message bodies older than retention_days
        to enforce data minimisation while preserving delivery counts.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # 1. Delete expired inbound messages
        inbound_stmt = delete(InboundMessage).where(InboundMessage.received_at < cutoff)
        in_res = await db.execute(inbound_stmt)

        # 2. Delete expired outbound messages
        outbound_stmt = delete(OutboundMessage).where(OutboundMessage.created_at < cutoff)
        out_res = await db.execute(outbound_stmt)

        await db.commit()

        purged_counts = {
            "inbound_purged": in_res.rowcount if hasattr(in_res, "rowcount") else 0,
            "outbound_purged": out_res.rowcount if hasattr(out_res, "rowcount") else 0,
            "retention_days": retention_days,
        }
        logger.info(f"Message retention purge completed: {purged_counts}")
        return purged_counts

    @classmethod
    async def purge_expired_disease_images(
        cls,
        db: AsyncSession,
        retention_days: int = 90,
    ) -> int:
        """Purges old disease diagnosis images from object storage if retention period has elapsed."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        stmt = select(DiseaseDetection).where(DiseaseDetection.created_at < cutoff)
        res = await db.execute(stmt)
        records = res.scalars().all()

        keys_to_delete = []
        for r in records:
            if r.image_s3_uri and "uploads/" in r.image_s3_uri:
                # Extract object key
                key = r.image_s3_uri.split("?")[0].replace("s3://", "").split("/", 1)[-1]
                keys_to_delete.append(key)

        deleted_count = storage_service.delete_objects(keys_to_delete)
        logger.info(f"Purged {deleted_count} expired disease images from storage.")
        return deleted_count

    @classmethod
    async def delete_farmer_data(
        cls,
        db: AsyncSession,
        user_id: str,
        redis_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive 'Right to be Forgotten' procedure:
        1. Identifies user and all associated farms, fields, advisories, detections, sessions.
        2. Purges user-uploaded images and documents from MinIO object storage.
        3. Flushes FSM session state and rate-limiting keys from Redis.
        4. Anonymizes audit log entries (sets user_id = NULL) to maintain tamper-evident audit trails.
        5. Permanently deletes database records (cascading delete on user, farm, fields, detections).
        """
        logger.info(f"Initiating 'Delete My Data' procedure for user_id={user_id}")

        # 1. Fetch user
        stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            logger.warning(f"User {user_id} not found for deletion.")
            return {"status": "not_found", "user_id": user_id}

        phone = user.phone_number if hasattr(user, "phone_number") else None
        phone_hash = None
        if phone:
            from app.messaging.crypto import hash_phone_number
            phone_hash = hash_phone_number(phone)

        # 2. Collect MinIO assets from DiseaseDetection
        dd_stmt = select(DiseaseDetection).where(DiseaseDetection.farmer_id == user_id)
        dd_res = await db.execute(dd_stmt)
        detections = dd_res.scalars().all()
        minio_keys = []
        for d in detections:
            if d.image_s3_uri:
                clean_key = d.image_s3_uri.split("?")[0].replace("s3://", "").split("/", 1)[-1]
                minio_keys.append(clean_key)

        minio_purged = storage_service.delete_objects(minio_keys)

        # 3. Anonymize Audit Logs (set user_id = None to preserve log integrity without PII)
        audit_update = update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
        await db.execute(audit_update)

        # 4. Count and delete message sessions
        msg_stmt = select(MessageSession).where(
            (MessageSession.linked_user_id == user_id) | 
            ((MessageSession.phone_hash == phone_hash) if phone_hash else False)
        )
        msg_res = await db.execute(msg_stmt)
        sessions = msg_res.scalars().all()
        session_count = len(sessions)
        for s in sessions:
            if s.phone_hash:
                await db.execute(delete(InboundMessage).where(InboundMessage.from_phone_hash == s.phone_hash))
                await db.execute(delete(OutboundMessage).where(OutboundMessage.to_phone_hash == s.phone_hash))
            await db.delete(s)

        # 5. Flush Redis keys if redis is available
        redis_purged = 0
        if redis_client:
            try:
                keys_to_del = [f"rate_limit:user:{user_id}", f"auth:token:{user_id}"]
                if phone_hash:
                    keys_to_del.extend([f"fsm:session:{phone_hash}", f"rate_limit:phone:{phone_hash}"])
                for k in keys_to_del:
                    await redis_client.delete(k)
                    redis_purged += 1
            except Exception as e:
                logger.warning(f"Redis cache purge partial error: {e}")

        # 6. Delete disease detections
        disease_count = len(detections)
        await db.execute(delete(DiseaseDetection).where(DiseaseDetection.farmer_id == user_id))

        # 7. Delete notifications
        await db.execute(delete(Notification).where(Notification.user_id == user_id))

        # 8. Delete consent
        await db.execute(delete(Consent).where(Consent.user_id == user_id))

        # 9. Delete User (will cascade to Farms, Fields, Advisories)
        await db.delete(user)
        await db.commit()

        result = {
            "status": "erased",
            "user_id": user_id,
            "purged_records": {
                "disease_detections": disease_count,
                "message_sessions": session_count,
                "minio_assets_purged": minio_purged,
                "redis_keys_cleared": redis_purged,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Successfully executed 'Delete My Data' for user_id={user_id}: {result}")
        return result
