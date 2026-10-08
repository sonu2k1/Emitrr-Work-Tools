"""
api_enricher.py - Optional enrichment connectors for Apollo.io and Hunter.io APIs.
"""
import os
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class APIEnricher:
    def __init__(self, apollo_key: Optional[str] = None, hunter_key: Optional[str] = None):
        self.apollo_key = apollo_key or os.getenv("APOLLO_API_KEY", "").strip()
        self.hunter_key = hunter_key or os.getenv("HUNTER_API_KEY", "").strip()

    def has_active_api(self) -> bool:
        return bool(self.apollo_key or self.hunter_key)

    def lookup_apollo(self, email: str, first_name: str = "", last_name: str = "", domain: str = "") -> Optional[Dict[str, Any]]:
        """
        Enriches contact using Apollo People Match API.
        """
        if not self.apollo_key or not email:
            return None

        url = "https://api.apollo.io/v1/people/match"
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.apollo_key
        }
        payload = {"email": email}
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if domain:
            payload["domain"] = domain

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                person = data.get("person")
                if person and person.get("title"):
                    org = person.get("organization") or {}
                    return {
                        "job_title": person.get("title", ""),
                        "company_name": org.get("name", ""),
                        "linkedin_url": person.get("linkedin_url", ""),
                        "seniority": person.get("seniority", ""),
                        "confidence": "High",
                        "source": "Apollo.io API"
                    }
        except Exception:
            pass
        return None

    def lookup_hunter(self, email: str, domain: str = "") -> Optional[Dict[str, Any]]:
        """
        Enriches contact using Hunter.io Email Verifier / Finder.
        """
        if not self.hunter_key or not email:
            return None

        url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={self.hunter_key}"
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                # Hunter returns sources if available
                # Note: Hunter's person finder endpoint
                # https://api.hunter.io/v2/email-finder
                return None
        except Exception:
            pass
        return None

    def enrich(self, email_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Runs active API enrichments."""
        email = email_info.get("email", "")
        first_name = email_info.get("first_name", "")
        last_name = email_info.get("last_name", "")
        domain = email_info.get("domain", "")

        # Try Apollo first
        if self.apollo_key:
            res = self.lookup_apollo(email, first_name, last_name, domain)
            if res and res.get("job_title"):
                return res

        return None
