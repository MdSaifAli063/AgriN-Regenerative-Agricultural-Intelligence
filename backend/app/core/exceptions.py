from fastapi import HTTPException, status


class EntityNotFoundException(HTTPException):
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} with identifier '{entity_id}' was not found."
        )


class ExternalServiceUnavailableException(HTTPException):
    def __init__(self, service_name: str, message: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External provider '{service_name}' failed: {message}"
        )


class HallucinationGuardException(HTTPException):
    def __init__(self, confidence_score: float, reason: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "HallucinationGuardTriggered",
                "confidence_score": confidence_score,
                "reason": reason,
                "advisory": "Confidence below threshold. Please consult a local agricultural extension officer."
            }
        )
