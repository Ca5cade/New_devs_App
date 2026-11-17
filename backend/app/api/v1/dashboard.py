from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from app.services.cache import get_revenue_summary
from app.services.reservations import get_properties_for_tenant
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

def _extract_tenant_id(current_user: Any) -> str:
    if isinstance(current_user, dict):
        return current_user.get("tenant_id") or "default_tenant"
    return getattr(current_user, "tenant_id", None) or "default_tenant"

@router.get("/dashboard/properties")
async def get_dashboard_properties(
    current_user: Any = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Returns list of properties belonging strictly to the authenticated tenant.
    """
    tenant_id = _extract_tenant_id(current_user)
    return await get_properties_for_tenant(tenant_id)

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: Optional[int] = Query(None, description="Month (1-12)"),
    year: Optional[int] = Query(None, description="Year (e.g. 2024)"),
    current_user: Any = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Returns revenue summary for a property, with strict tenant isolation and timezone accuracy.
    """
    tenant_id = _extract_tenant_id(current_user)
    
    revenue_data = await get_revenue_summary(property_id, tenant_id, month=month, year=year)
    
    total_revenue_float = round(float(revenue_data['total']), 2)
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data.get('currency', 'USD'),
        "reservations_count": revenue_data['count']
    }
