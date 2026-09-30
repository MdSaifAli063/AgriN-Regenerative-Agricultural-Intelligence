import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user_token_payload,
    get_password_hash,
    verify_password
)
from app.models.user import BricsCountry, FarmerConsent, User
from app.schemas.user import (
    BricsCountrySchema,
    ConsentUpdate,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication & Farmer Identity"])


@router.get("/countries", response_model=List[BricsCountrySchema])
async def list_brics_countries(db: AsyncSession = Depends(get_db)):
    """List all registered BRICS partner nations."""
    result = await db.execute(select(BricsCountry).where(BricsCountry.is_active == True))
    countries = result.scalars().all()
    if not countries and settings.DEMO_MODE:
        # Return fallback BRICS countries for hackathon demo
        return [
            BricsCountrySchema(
                code="IND",
                name="India",
                national_registry_url="https://agricoop.nic.in",
                contact_agency="ICAR / Department of Agriculture & Farmers Welfare",
                is_active=True
            ),
            BricsCountrySchema(
                code="BRA",
                name="Brazil",
                national_registry_url="https://embrapa.br",
                contact_agency="EMBRAPA / Ministério da Agricultura e Pecuária",
                is_active=True
            ),
            BricsCountrySchema(
                code="ZAF",
                name="South Africa",
                national_registry_url="https://arc.agric.za",
                contact_agency="Agricultural Research Council (ARC)",
                is_active=True
            ),
            BricsCountrySchema(
                code="CHN",
                name="China",
                national_registry_url="https://caas.cn",
                contact_agency="Chinese Academy of Agricultural Sciences (CAAS)",
                is_active=True
            ),
            BricsCountrySchema(
                code="RUS",
                name="Russia",
                national_registry_url="https://mcx.gov.ru",
                contact_agency="Ministry of Agriculture of the Russian Federation",
                is_active=True
            )
        ]
    return countries


@router.post("/register", response_model=TokenResponse)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new farmer or agricultural officer."""
    # Check if user already exists
    if user_in.phone_number:
        existing = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number is already registered."
            )

    hashed_pw = get_password_hash(user_in.password) if user_in.password else None
    new_user = User(
        id=str(uuid.uuid4()),
        country_code=user_in.country_code,
        phone_number=user_in.phone_number,
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        preferred_language=user_in.preferred_language,
        role=user_in.role,
        is_verified=True
    )
    db.add(new_user)
    
    # Initialize consent defaults
    consent = FarmerConsent(
        farmer_id=new_user.id,
        share_anonymized_soil=True,
        share_disease_telemetry=True,
        participate_in_federated_learning=True
    )
    db.add(consent)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "phone": new_user.phone_number,
        "role": new_user.role,
        "country": new_user.country_code,
        "name": new_user.full_name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login via phone, email, or OTP demo."""
    # Look up user by phone or email
    query = select(User).where(
        (User.phone_number == credentials.phone_or_email) | (User.email == credentials.phone_or_email)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        if settings.DEMO_MODE:
            # Automatic instant onboarding for demo presentation
            user = User(
                id="demo-farmer-id-india-001",
                country_code="IND",
                phone_number=credentials.phone_or_email,
                full_name="Ramesh Patil (Demo Farmer)",
                preferred_language="hi",
                role="farmer",
                is_verified=True
            )
            try:
                db.add(user)
                await db.commit()
                await db.refresh(user)
            except Exception:
                await db.rollback()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or user not found."
            )

    token = create_access_token({
        "sub": user.id,
        "phone": user.phone_number,
        "role": user.role,
        "country": user.country_code,
        "name": user.full_name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    payload: dict = Depends(get_current_user_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve active authenticated profile."""
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        if settings.DEMO_MODE:
            return UserResponse(
                id=user_id or "demo-farmer-id-india-001",
                country_code=payload.get("country", "IND"),
                phone_number=payload.get("phone", "+919876543210"),
                email=None,
                full_name=payload.get("name", "Ramesh Patil"),
                preferred_language="hi",
                role=payload.get("role", "farmer"),
                is_verified=True,
                created_at=datetime.utcnow()
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    return UserResponse.model_validate(user)


@router.put("/consent")
async def update_consent(
    consent_in: ConsentUpdate,
    payload: dict = Depends(get_current_user_token_payload),
    db: AsyncSession = Depends(get_db)
):
    """Update farmer privacy and data-sharing preferences."""
    user_id = payload.get("sub")
    result = await db.execute(select(FarmerConsent).where(FarmerConsent.farmer_id == user_id))
    consent = result.scalar_one_or_none()

    if not consent:
        consent = FarmerConsent(farmer_id=user_id)
        db.add(consent)

    consent.share_anonymized_soil = consent_in.share_anonymized_soil
    consent.share_disease_telemetry = consent_in.share_disease_telemetry
    consent.participate_in_federated_learning = consent_in.participate_in_federated_learning
    await db.commit()

    return {"status": "success", "message": "Consent preferences updated successfully."}
