import json
import logging

import requests

from jez_face_api.config import settings

logger = logging.getLogger(__name__)


class LaravelSync:
    def __init__(self) -> None:
        self.api_url = settings.LARAVEL_API_URL.rstrip("/")
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if settings.LARAVEL_API_TOKEN:
            self.headers["X-Internal-Token"] = settings.LARAVEL_API_TOKEN

    def get_users_face_data(self) -> dict[int, dict]:
        try:
            response = requests.get(
                f"{self.api_url}/v1/admin/face-data/all",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to fetch face data from Laravel: %s", exc)
            return {}

        if payload.get("status") != "success":
            logger.warning("Laravel returned error: %s", payload.get("message"))
            return {}

        users_face_data: dict[int, dict] = {}
        for user_data in payload.get("data", []):
            user_id = user_data.get("id")
            face_data_json = user_data.get("u_face")
            if not user_id or not face_data_json:
                continue

            try:
                face_data = json.loads(face_data_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse face data for user %s", user_id)
                continue

            samples = self._extract_samples(face_data)
            if samples:
                users_face_data[int(user_id)] = {
                    "samples": samples,
                    "samples_count": len(samples),
                    "model": face_data.get("model", "unknown")
                    if isinstance(face_data, dict)
                    else "unknown",
                    "registered_at": face_data.get("registered_at")
                    if isinstance(face_data, dict)
                    else None,
                }

        return users_face_data

    def get_user_details(self, user_id: int) -> dict:
        try:
            response = requests.get(
                f"{self.api_url}/v1/admin/users/{user_id}",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to fetch user details for %s: %s", user_id, exc)
            return {"name": "Unknown", "email": "", "phone": ""}

        if payload.get("status") != "success":
            return {"name": "Unknown", "email": "", "phone": ""}

        user = payload.get("data", {})
        return {
            "name": user.get("u_name", "Unknown"),
            "email": user.get("u_email", ""),
            "phone": user.get("u_phone", ""),
        }

    @staticmethod
    def _extract_samples(face_data: object) -> list[list[float]]:
        if isinstance(face_data, dict):
            raw_samples = face_data.get("samples") or face_data.get("descriptors") or []
        elif isinstance(face_data, list):
            raw_samples = face_data
        else:
            raw_samples = []

        valid_samples: list[list[float]] = []
        for sample in raw_samples:
            if isinstance(sample, list) and sample:
                valid_samples.append(sample)
            elif isinstance(sample, dict) and isinstance(sample.get("descriptor"), list):
                valid_samples.append(sample["descriptor"])
        return valid_samples


laravel_sync = LaravelSync()
