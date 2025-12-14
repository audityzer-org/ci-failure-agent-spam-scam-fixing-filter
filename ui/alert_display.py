"""Alert Display UI Components.

This module provides Flask/web components for displaying alerts with action buttons.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    PENDING = "pending"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class ActionButton:
    """Represents an action button in the UI."""
    id: str
    label: str
    action_type: str
    color: str = "primary"
    icon: Optional[str] = None
    confirmation_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "action_type": self.action_type,
            "color": self.color,
            "icon": self.icon,
            "confirmation_required": self.confirmation_required
        }


@dataclass
class AlertDisplay:
    """Alert display model for UI rendering."""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    timestamp: str
    source: str
    tags: List[str]
    actions: List[ActionButton]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "tags": self.tags,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata
        }
    
    def to_html(self) -> str:
        """Generate HTML representation."""
        severity_color = {
            AlertSeverity.CRITICAL: "#dc3545",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.LOW: "#17a2b8",
            AlertSeverity.INFO: "#0d6efd"
        }
        
        html = f"""
        <div class="alert alert-{self.severity.value}" style="border-left: 4px solid {severity_color[self.severity]}">
            <div class="alert-header">
                <span class="alert-title">{self.title}</span>
                <span class="badge badge-{self.status.value}">{self.status.value.upper()}</span>
            </div>
            <div class="alert-body">
                <p class="alert-description">{self.description}</p>
                <div class="alert-metadata">
                    <span class="badge badge-secondary">{self.source}</span>
                    <span class="badge badge-secondary">{self.timestamp}</span>
                </div>
            </div>
            <div class="alert-actions">
        """
        
        for action in self.actions:
            html += f"""
                <button class="btn btn-{action.color} btn-sm" 
                        data-action="{action.action_type}" 
                        data-alert-id="{self.alert_id}"
                        onclick="executeAction('{self.alert_id}', '{action.action_type}')">
                    {action.label}
                </button>
            """
        
        html += """
            </div>
        </div>
        """
        return html


class AlertPanel:
    """Manages a panel of alerts with real-time updates."""
    
    def __init__(self):
        """Initialize alert panel."""
        self.alerts: Dict[str, AlertDisplay] = {}
        self.alert_order: List[str] = []  # To maintain insertion order
    
    def add_alert(self, alert: AlertDisplay) -> None:
        """Add an alert to the panel."""
        self.alerts[alert.alert_id] = alert
        if alert.alert_id not in self.alert_order:
            self.alert_order.append(alert.alert_id)
    
    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert from the panel."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            if alert_id in self.alert_order:
                self.alert_order.remove(alert_id)
            return True
        return False
    
    def update_alert_status(self, alert_id: str, status: AlertStatus) -> bool:
        """Update alert status."""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = status
            return True
        return False
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[AlertDisplay]:
        """Get alerts filtered by severity."""
        return [
            self.alerts[aid] for aid in self.alert_order
            if self.alerts[aid].severity == severity
        ]
    
    def get_critical_alerts(self) -> List[AlertDisplay]:
        """Get all critical alerts."""
        return self.get_alerts_by_severity(AlertSeverity.CRITICAL)
    
    def get_active_alerts(self) -> List[AlertDisplay]:
        """Get all active alerts."""
        return [
            self.alerts[aid] for aid in self.alert_order
            if self.alerts[aid].status == AlertStatus.ACTIVE
        ]
    
    def get_all_alerts(self) -> List[AlertDisplay]:
        """Get all alerts in insertion order."""
        return [self.alerts[aid] for aid in self.alert_order]
    
    def to_json(self) -> str:
        """Convert alerts to JSON."""
        alerts_data = [self.alerts[aid].to_dict() for aid in self.alert_order]
        return json.dumps(alerts_data)
    
    def generate_html_panel(self) -> str:
        """Generate HTML for the entire alert panel."""
        html = '<div class="alert-panel">'
        for alert_id in self.alert_order:
            html += self.alerts[alert_id].to_html()
        html += '</div>'
        return html
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        severities = {s: 0 for s in AlertSeverity}
        statuses = {s: 0 for s in AlertStatus}
        
        for alert in self.get_all_alerts():
            severities[alert.severity] += 1
            statuses[alert.status] += 1
        
        return {
            "total_alerts": len(self.alerts),
            "critical": severities[AlertSeverity.CRITICAL],
            "high": severities[AlertSeverity.HIGH],
            "medium": severities[AlertSeverity.MEDIUM],
            "low": severities[AlertSeverity.LOW],
            "info": severities[AlertSeverity.INFO],
            "active": statuses[AlertStatus.ACTIVE],
            "pending": statuses[AlertStatus.PENDING],
            "resolved": statuses[AlertStatus.RESOLVED]
        }
