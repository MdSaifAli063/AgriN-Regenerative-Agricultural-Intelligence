from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ConsentUpdateRequest(BaseModel):
    share_anonymized_soil: bool = True
    share_outbreak_telemetry: bool = True
    participate_in_federated_learning: bool = True


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    share_anonymized_soil: bool
    share_outbreak_telemetry: bool
    participate_in_federated_learning: bool
    updated_at: datetime
