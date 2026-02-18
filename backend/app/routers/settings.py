from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setting
from app.schemas.schemas import SettingsOut, SettingsUpdate

router = APIRouter()

DEFAULTS = {
    "wasabi_cost_per_tb": 6.99,
    "sales_tax_rate": 0.0685,
    "discrepancy_threshold_pct": 20.0,
    "low_disk_threshold_pct": 20.0,
    "deleted_ratio_threshold": 0.5,
}


def _read_settings(db: Session) -> dict:
    """Read all settings from DB, falling back to defaults for missing keys."""
    rows = db.query(Setting).all()
    db_values = {row.key: row.value for row in rows}

    result = {}
    for key, default in DEFAULTS.items():
        raw = db_values.get(key, default)
        # The value column is JSONB, so it may already be the correct type
        # but could also be wrapped in a dict or stored as a string.
        if isinstance(raw, dict) and "value" in raw:
            result[key] = float(raw["value"])
        else:
            result[key] = float(raw)
    return result


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    values = _read_settings(db)
    return SettingsOut(**values)


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    updates = body.model_dump(exclude_unset=True)

    for key, value in updates.items():
        existing = db.query(Setting).filter(Setting.key == key).first()
        if existing:
            existing.value = value
        else:
            db.add(Setting(key=key, value=value))

    db.commit()

    values = _read_settings(db)
    return SettingsOut(**values)
