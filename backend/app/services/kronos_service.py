from __future__ import annotations

import os
import uuid
from collections.abc import Iterable
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.auth import HTTPDigestAuth


class KronosDeviceError(RuntimeError):
    pass


def _device_url(value: str) -> str:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("La URL del dispositivo debe usar HTTP o HTTPS.")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("La URL del dispositivo no admite credenciales ni fragmentos.")
    return urlunsplit(parsed)


def attendance_endpoint(device_url: str) -> str:
    parsed = urlsplit(_device_url(device_url))
    query = "&".join(
        item
        for item in parsed.query.split("&")
        if item and item.split("=", 1)[0].lower() not in {"security", "iv"}
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def people_endpoint(device_url: str, action: str) -> str:
    base = _device_url(device_url)
    return urljoin(
        base if base.endswith("/") else f"{base}/",
        f"/ISAPI/AccessControl/UserInfo/{action}?format=json",
    )


def summarize_attendance(events: Iterable[dict], people: Iterable[dict] = ()) -> list[dict]:
    people_by_employee = {str(person.get("employeeNo")): person for person in people}
    groups: dict[tuple[str, str], dict] = {}
    for event in events:
        timestamp = str(event.get("time") or "")
        if len(timestamp) < 10:
            continue
        employee = str(event.get("employeeNoString") or event.get("name") or "Sin identificador")
        person = people_by_employee.get(employee, {})
        day = timestamp[:10]
        key = (employee, day)
        current = groups.setdefault(
            key,
            {
                "employee": employee,
                "name": person.get("name") or event.get("name") or "",
                "date": day,
                "firstEntry": timestamp,
                "lastExit": timestamp,
                "marks": 0,
                "door": event.get("doorNo") or "",
                "verification": event.get("currentVerifyMode") or "",
            },
        )
        current["firstEntry"] = min(current["firstEntry"], timestamp)
        current["lastExit"] = max(current["lastExit"], timestamp)
        current["marks"] += 1
    rows = sorted(groups.values(), key=lambda row: row["employee"])
    return sorted(rows, key=lambda row: row["date"], reverse=True)


def _time_minutes(value: str) -> int:
    return datetime.fromisoformat(value).hour * 60 + datetime.fromisoformat(value).minute


def attendance_statistics(report: Iterable[dict]) -> list[dict]:
    employees: dict[str, dict] = {}
    for row in report:
        employee = str(row["employee"])
        current = employees.setdefault(
            employee,
            {
                "employee": employee,
                "name": row.get("name") or "",
                "days": 0,
                "marks": 0,
                "totalFirstMinutes": 0,
                "totalLastMinutes": 0,
                "totalWorkedMinutes": 0,
            },
        )
        first_minutes = _time_minutes(row["firstEntry"])
        last_minutes = _time_minutes(row["lastExit"])
        current["days"] += 1
        current["marks"] += int(row["marks"])
        current["totalFirstMinutes"] += first_minutes
        current["totalLastMinutes"] += last_minutes
        current["totalWorkedMinutes"] += max(0, last_minutes - first_minutes)

    result = []
    for employee in employees.values():
        result.append(
            {
                "employee": employee["employee"],
                "name": employee["name"],
                "days": employee["days"],
                "marks": employee["marks"],
                "averageEntryMinutes": round(employee["totalFirstMinutes"] / employee["days"]),
                "averageExitMinutes": round(employee["totalLastMinutes"] / employee["days"]),
                "estimatedHours": round(employee["totalWorkedMinutes"] / 60, 1),
            }
        )
    return sorted(result, key=lambda row: (row["name"], row["employee"]))


class KronosService:
    def __init__(self, config: dict):
        self.device_url = _device_url(config.get("deviceUrl"))
        self.username = str(config.get("username") or "")
        self.password = str(config.get("password") or "")
        if not self.username or not self.password:
            raise ValueError("Completa el usuario y la contraseña del dispositivo.")
        self.session_tag = str(config.get("sessionTag") or "")
        self.cookie = str(config.get("cookie") or "")
        self.verify_tls = not bool(config.get("allowSelfSigned", False))
        self.timeout = float(os.getenv("KRONOS_REQUEST_TIMEOUT_SECONDS", "20"))
        self.max_records = int(os.getenv("KRONOS_MAX_RECORDS", "10000"))
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(self.username, self.password)
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "User-Agent": "Tyakxa-Kronos/1.0",
            }
        )
        if self.session_tag:
            self.session.headers["SessionTag"] = self.session_tag
        if self.cookie:
            self.session.headers["Cookie"] = self.cookie

    def _request(self, url: str, payload: dict, method: str = "POST") -> dict:
        try:
            response = self.session.request(
                method,
                url,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise KronosDeviceError(
                "No fue posible completar la operación con el dispositivo."
            ) from exc

    def fetch_attendance(self, start_time: str, end_time: str) -> list[dict]:
        events: list[dict] = []
        search_id = uuid.uuid4().hex
        while len(events) < self.max_records:
            payload = {
                "AcsEventCond": {
                    "searchID": search_id,
                    "searchResultPosition": len(events),
                    "maxResults": min(100, self.max_records - len(events)),
                    "major": 5,
                    "minor": 75,
                    "startTime": start_time,
                    "endTime": end_time,
                    "timeReverseOrder": True,
                }
            }
            result = self._request(attendance_endpoint(self.device_url), payload).get(
                "AcsEvent", {}
            )
            page = result.get("InfoList") or []
            events.extend(page)
            if result.get("responseStatusStrg") != "MORE" or not page:
                break
        return events

    def fetch_people(self) -> list[dict]:
        people: list[dict] = []
        search_id = uuid.uuid4().hex
        while len(people) < self.max_records:
            payload = {
                "UserInfoSearchCond": {
                    "searchID": search_id,
                    "searchResultPosition": len(people),
                    "maxResults": min(100, self.max_records - len(people)),
                }
            }
            result = self._request(people_endpoint(self.device_url, "Search"), payload).get(
                "UserInfoSearch", {}
            )
            page = result.get("UserInfo") or []
            people.extend(page)
            if result.get("responseStatusStrg") != "MORE" or not page:
                break
        return people

    def save_person(self, person: dict) -> dict:
        return self._request(people_endpoint(self.device_url, "SetUp"), {"UserInfo": person}, "PUT")

    def delete_person(self, employee_no: str) -> dict:
        payload = {"UserInfoDelCond": {"EmployeeNoList": [{"employeeNo": employee_no}]}}
        return self._request(people_endpoint(self.device_url, "Delete"), payload, "PUT")
