from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.application.services.summary_service import SummaryGatewayService
from app.presentation.api.dependencies import get_summary_gateway_service
from app.presentation.schemas import ErrorResponseSchema, SummaryRequestSchema, SummaryResponseSchema

router = APIRouter(tags=['internal'])


@router.post('/internal/summaries', response_model=SummaryResponseSchema, responses={502: {'model': ErrorResponseSchema}})
def summarize(payload: SummaryRequestSchema, service: SummaryGatewayService = Depends(get_summary_gateway_service)):
    try:
        result = service.summarize(payload)
        if hasattr(result, 'model_dump'):
            result = result.model_dump(by_alias=True)
        return SummaryResponseSchema.model_validate(result)
    except PydanticValidationError as e:
        error = ErrorResponseSchema(
            code='summary_contract_violation',
            message='Summary response did not satisfy the required schema.',
            details=str(e),
        )
        return JSONResponse(status_code=502, content=error.model_dump())
    except Exception as e:
        error = ErrorResponseSchema(
            code='summary_generation_failed',
            message='Summary generation failed.',
            details=str(e),
        )
        return JSONResponse(status_code=502, content=error.model_dump())
