from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db

router = APIRouter(prefix="/adaptive", tags=["adaptive"])


@router.post("/build-order/retrain", dependencies=[Depends(require_admin)])
def retrain_build_order_classifier(db: Session = Depends(get_db)):
    """
    Retrain the K-Means build order classifier on all available data.
    """
    from ..services.build_order_classifier import train_classifier

    try:
        result = train_classifier(db)
        return {
            "status": "success",
            "message": "Build order classifier retrained",
            "details": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")
