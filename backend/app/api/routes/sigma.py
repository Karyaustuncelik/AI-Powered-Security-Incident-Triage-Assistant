"""API routes for SIGMA rule generation and compliance mapping.

These endpoints take an incident ID and return:
  - SIGMA detection rules (YAML)
  - Splunk SPL queries
  - KQL queries (for Microsoft Sentinel)
  - Compliance framework mappings
  - Anomaly detection reports
"""

from fastapi import APIRouter, HTTPException

from app.services.anomaly_service import get_anomaly_detector
from app.services.compliance_service import get_compliance_mapper
from app.services.incidents_service import get_incidents_service
from app.services.sigma_service import get_sigma_generator

router = APIRouter(prefix="/detection", tags=["detection-engineering"])


@router.get("/sigma/{incident_id}")
def generate_sigma_rule(incident_id: str) -> dict:
    """Generate a SIGMA detection rule from an incident."""
    service = get_incidents_service()
    incident = service.get_enriched_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    gen = get_sigma_generator()
    return {
        "incident_id": incident_id,
        "sigma_rule": gen.generate(incident),
        "splunk_spl": gen.generate_splunk_spl(incident),
        "kql": gen.generate_kql(incident),
    }


@router.get("/compliance/{incident_id}")
def get_compliance_mapping(incident_id: str) -> dict:
    """Map an incident to compliance framework controls."""
    service = get_incidents_service()
    incident = service.get_enriched_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    mapper = get_compliance_mapper()
    return mapper.get_summary(incident)


@router.get("/anomaly/{incident_id}")
def get_anomaly_report(incident_id: str) -> dict:
    """Get statistical anomaly analysis for an incident."""
    service = get_incidents_service()
    incident = service.get_enriched_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # We need the raw record for anomaly detection
    raw = service.get_raw_record(incident_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Raw record not found.")

    detector = get_anomaly_detector()
    return detector.analyze(raw).to_dict()
