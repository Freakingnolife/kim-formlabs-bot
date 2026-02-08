"""
CSI: Print Crime Scene Investigation

AI-powered analysis of failed 3D print photos.
Diagnoses issues and suggests fixes.

Author: Kim (OpenClaw)
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CSIFinding:
    """A single finding from CSI analysis."""
    issue_type: Literal[
        "support_failure", "layer_shift", "warping", "resin_contamination",
        "under_exposure", "over_exposure", " peel_force_damage", "dimensional_error",
        "surface_defect", "incomplete_print", "unknown"
    ]
    severity: Literal["critical", "major", "minor", "cosmetic"]
    description: str
    location: str | None = None  # e.g., "base", "overhang", "layer 45"
    confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class CSIDiagnosis:
    """Complete diagnosis from CSI analysis."""
    primary_issue: str
    summary: str
    findings: list[CSIFinding]
    root_cause: str
    suggested_fixes: list[dict]
    prevention_tips: list[str]
    confidence_score: float


# ============================================================================
# CSI Analyzer
# ============================================================================

class CSIAnalyzer:
    """Analyze failed 3D print photos using AI vision."""
    
    # OpenAI Vision API endpoint
    API_URL = "https://api.openai.com/v1/chat/completions"
    
    # System prompt for print analysis
    SYSTEM_PROMPT = """You are an expert 3D printing forensic analyst specializing in resin (SLA/DLP) prints.

Analyze the provided image of a failed 3D print and identify:

1. **Failure Type** (choose most likely):
   - support_failure: Supports detached or failed
   - layer_shift: Layers misaligned
   - warping: Corners curled, part deformed
   - resin_contamination: Cloudy, discolored, or particulates
   - under_exposure: Soft, incomplete, or missing features
   - over_exposure: Bulging, fused details, elephant foot
   - peel_force_damage: Tears, delamination between layers
   - dimensional_error: Wrong size, shrinkage issues
   - surface_defect: Rough surface, pitting, or artifacts
   - incomplete_print: Print stopped mid-way
   - unknown: Cannot determine

2. **Severity**: critical, major, minor, or cosmetic

3. **Location**: Where on the print (base, overhang, specific layer, etc.)

4. **Root Cause**: Brief explanation of WHY this happened

5. **Suggested Fixes**: 2-3 specific actionable solutions

6. **Prevention Tips**: How to avoid this in future prints

Respond in JSON format:
{
  "primary_issue": "issue_type",
  "summary": "brief description of what you see",
  "findings": [
    {
      "issue_type": "...",
      "severity": "...",
      "description": "...",
      "location": "...",
      "confidence": 0.95
    }
  ],
  "root_cause": "explanation",
  "suggested_fixes": [
    {"action": "...", "details": "..."}
  ],
  "prevention_tips": ["tip1", "tip2"],
  "confidence_score": 0.9
}

Be thorough but concise. Use your knowledge of resin printing physics and common failure modes."""

    def __init__(self, api_key: str | None = None):
        """Initialize CSI analyzer."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
    
    def analyze(self, image_path: str | Path) -> CSIDiagnosis:
        """
        Analyze a failed print photo.
        
        Args:
            image_path: Path to image file (jpg, png)
            
        Returns:
            CSIDiagnosis with findings and recommendations
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine MIME type
        mime_type = self._get_mime_type(image_path)
        
        # Build API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this failed 3D print and provide diagnosis in JSON format."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.3
        }
        
        # Make API call
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            # Sometimes GPT wraps JSON in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Convert to CSIDiagnosis
            findings = [
                CSIFinding(
                    issue_type=f.get("issue_type", "unknown"),
                    severity=f.get("severity", "minor"),
                    description=f.get("description", ""),
                    location=f.get("location"),
                    confidence=f.get("confidence", 0.5)
                )
                for f in data.get("findings", [])
            ]
            
            return CSIDiagnosis(
                primary_issue=data.get("primary_issue", "unknown"),
                summary=data.get("summary", "No summary available"),
                findings=findings,
                root_cause=data.get("root_cause", "Unknown"),
                suggested_fixes=data.get("suggested_fixes", []),
                prevention_tips=data.get("prevention_tips", []),
                confidence_score=data.get("confidence_score", 0.5)
            )
            
        except requests.exceptions.Timeout:
            raise RuntimeError("Analysis timed out. Try again with a smaller image.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse analysis result: {e}")
    
    def _get_mime_type(self, path: Path) -> str:
        """Determine MIME type from file extension."""
        ext = path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        return mime_types.get(ext, "image/jpeg")
    
    def quick_check(self, image_path: str | Path) -> str:
        """
        Quick analysis without full diagnosis.
        Returns a brief summary suitable for chat.
        """
        try:
            diagnosis = self.analyze(image_path)
            
            # Format brief response
            emoji = {
                "critical": "🚨",
                "major": "⚠️",
                "minor": "🔶",
                "cosmetic": "🔧"
            }.get(diagnosis.findings[0].severity if diagnosis.findings else "minor", "🔍")
            
            response = f"""{emoji} *CSI Analysis*

*Issue:* {diagnosis.primary_issue.replace('_', ' ').title()}
*Confidence:* {diagnosis.confidence_score:.0%}

{diagnosis.summary}

*Root Cause:*
{diagnosis.root_cause}

*Quick Fix:*
{diagnosis.suggested_fixes[0]['action'] if diagnosis.suggested_fixes else 'No specific fix available'}"""
            
            return response
            
        except Exception as e:
            return f"❌ Analysis failed: {str(e)}"


# ============================================================================
# Command Handlers
# ============================================================================

def cmd_csi(image_path: str, api_key: str | None = None) -> str:
    """
    Handle /csi command - full analysis report.
    
    Args:
        image_path: Path to uploaded image
        api_key: OpenAI API key (optional, reads from env)
    """
    try:
        analyzer = CSIAnalyzer(api_key)
        diagnosis = analyzer.analyze(image_path)
        
        # Build detailed report
        lines = [
            "🔍 *CSI: Print Crime Scene Investigation*\n",
            f"*Primary Issue:* {diagnosis.primary_issue.replace('_', ' ').title()}",
            f"*Confidence:* {diagnosis.confidence_score:.0%}\n",
            f"*Summary:*\n{diagnosis.summary}\n",
            "*Findings:*"
        ]
        
        for finding in diagnosis.findings[:3]:  # Top 3
            emoji = {"critical": "🚨", "major": "⚠️", "minor": "🔶", "cosmetic": "🔧"}.get(
                finding.severity, "🔍"
            )
            lines.append(f"{emoji} {finding.description}")
            if finding.location:
                lines.append(f"   Location: {finding.location}")
            lines.append(f"   Confidence: {finding.confidence:.0%}")
            lines.append("")
        
        lines.extend([
            f"*Root Cause:*\n{diagnosis.root_cause}\n",
            "*Suggested Fixes:*"
        ])
        
        for i, fix in enumerate(diagnosis.suggested_fixes[:3], 1):
            action = fix.get("action", "Unknown fix")
            details = fix.get("details", "")
            lines.append(f"{i}. {action}")
            if details:
                lines.append(f"   {details}")
        
        lines.extend(["", "*Prevention Tips:*"])
        for tip in diagnosis.prevention_tips[:3]:
            lines.append(f"• {tip}")
        
        return "\n".join(lines)
        
    except FileNotFoundError:
        return "❌ Image file not found. Please upload a photo first."
    except ValueError as e:
        return f"❌ {str(e)}"
    except RuntimeError as e:
        return f"❌ Analysis error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"


def cmd_analyze(image_path: str, api_key: str | None = None) -> str:
    """
    Handle /analyze command - quick analysis.
    
    Args:
        image_path: Path to uploaded image
        api_key: OpenAI API key (optional, reads from env)
    """
    try:
        analyzer = CSIAnalyzer(api_key)
        return analyzer.quick_check(image_path)
    except Exception as e:
        return f"❌ Analysis failed: {str(e)}"


# ============================================================================
# Issue Type Reference
# ============================================================================

ISSUE_DESCRIPTIONS = {
    "support_failure": {
        "description": "Support structures detached or failed to hold the part",
        "common_causes": ["Insufficient support density", "Weak support tips", "High peel forces"],
        "fixes": [
            "Increase support density to 70-80%",
            "Use heavier support type",
            "Add supports to all overhangs >45°",
            "Increase support tip diameter"
        ]
    },
    "layer_shift": {
        "description": "Layers misaligned or shifted horizontally",
        "common_causes": ["Build platform loose", "Resin tank issues", "High peel forces"],
        "fixes": [
            "Relevel build platform",
            "Check resin tank for debris",
            "Reduce layer exposure time",
            "Increase wait time between layers"
        ]
    },
    "warping": {
        "description": "Corners curled up or part deformed",
        "common_causes": ["Uneven shrinkage", "Insufficient supports on base", "High stress"],
        "fixes": [
            "Add supports to base edges",
            "Reorient part to reduce overhang",
            "Increase base layer count",
            "Use Tough resin for large parts"
        ]
    },
    "resin_contamination": {
        "description": "Cloudy areas, particulates, or discoloration",
        "common_causes": ["Dirty resin tank", "Contaminated resin", "Failed print debris"],
        "fixes": [
            "Clean resin tank thoroughly",
            "Filter resin through paint strainer",
            "Replace resin if heavily contaminated",
            "Clean build platform"
        ]
    },
    "under_exposure": {
        "description": "Soft, incomplete, or missing features",
        "common_causes": ["Insufficient exposure time", "Weak light source", "Wrong material settings"],
        "fixes": [
            "Increase exposure time by 20%",
            "Check resin is not expired",
            "Verify material profile is correct",
            "Clean optical window"
        ]
    },
    "over_exposure": {
        "description": "Bulging features, fused details, elephant foot",
        "common_causes": ["Too much exposure", "High power setting", "Longer light-on time"],
        "fixes": [
            "Reduce exposure time by 15%",
            "Enable anti-aliasing",
            "Lower light intensity if adjustable",
            "Use grayscale calibration"
        ]
    },
    "peel_force_damage": {
        "description": "Tears, delamination, or Z-axis artifacts",
        "common_causes": ["High peel forces", "Large surface area", "Fast peel speed"],
        "fixes": [
            "Reduce peel speed",
            "Increase lift height",
            "Add drain holes to hollow parts",
            "Orient to minimize cross-section"
        ]
    },
    "incomplete_print": {
        "description": "Print stopped before completion",
        "common_causes": ["Power failure", "Out of resin", "Hardware error"],
        "fixes": [
            "Check resin level before printing",
            "Ensure stable power supply",
            "Check for error messages on printer",
            "Reduce print time with faster settings"
        ]
    }
}


def get_issue_info(issue_type: str) -> dict:
    """Get information about a specific issue type."""
    return ISSUE_DESCRIPTIONS.get(issue_type, {
        "description": "Unknown issue type",
        "common_causes": [],
        "fixes": []
    })


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python csi_analyzer.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("🔍 Analyzing failed print...")
    print(cmd_analyze(image_path))
