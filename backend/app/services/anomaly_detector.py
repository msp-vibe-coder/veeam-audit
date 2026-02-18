"""
Anomaly detection service.

Compares consecutive daily summaries and flags large changes as anomalies.
This is a stub that can be expanded with actual detection logic.
"""

from sqlalchemy.orm import Session

from app.models import DailySummary, Anomaly


def detect_anomalies(db: Session) -> list[Anomaly]:
    """
    Analyze recent daily summaries for anomalies.

    Compares the two most recent daily summaries and flags significant changes
    in key metrics (veeam_tb, wasabi_active_tb, total_cost, etc.).

    Returns:
        List of newly created Anomaly records.
    """
    summaries = (
        db.query(DailySummary)
        .order_by(DailySummary.report_date.desc())
        .limit(2)
        .all()
    )

    if len(summaries) < 2:
        return []

    current = summaries[0]
    previous = summaries[1]

    created_anomalies: list[Anomaly] = []

    # Define thresholds for each metric
    checks = [
        ("veeam_tb", "Veeam backup size", 20.0),
        ("wasabi_active_tb", "Wasabi active storage", 20.0),
        ("wasabi_deleted_tb", "Wasabi deleted storage", 50.0),
        ("total_cost", "Total cost", 25.0),
    ]

    for attr, label, threshold_pct in checks:
        prev_val = float(getattr(previous, attr) or 0)
        curr_val = float(getattr(current, attr) or 0)

        if prev_val == 0:
            continue

        change_pct = abs(curr_val - prev_val) / prev_val * 100

        if change_pct >= threshold_pct:
            severity = "critical" if change_pct >= threshold_pct * 2 else "warning"
            direction = "increased" if curr_val > prev_val else "decreased"

            anomaly = Anomaly(
                report_date=current.report_date,
                severity=severity,
                type="metric_change",
                metric=attr,
                previous_value=prev_val,
                current_value=curr_val,
                change_pct=round(change_pct, 2),
                description=(
                    f"{label} {direction} by {change_pct:.1f}% "
                    f"(from {prev_val:.4f} to {curr_val:.4f})"
                ),
            )
            db.add(anomaly)
            created_anomalies.append(anomaly)

    if created_anomalies:
        db.commit()

    return created_anomalies
