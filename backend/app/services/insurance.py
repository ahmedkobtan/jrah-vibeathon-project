from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Protocol

from .sqlite_repositories import SQLiteConfig


@dataclass
class InsuranceMatch:
    plan_id: str
    payer_name: str
    network_id: Optional[str]
    coverage_percent: Optional[float]
    deductible: Optional[float]
    match_score: float


class InsuranceMatcher(Protocol):
    async def match(self, name: str) -> Optional[InsuranceMatch]:
        ...

    async def suggest(self, prefix: str) -> List[InsuranceMatch]:
        ...


@dataclass
class InsurancePlanRecord:
    plan_id: str
    payer_name: str
    network_id: Optional[str]
    coverage_percent: Optional[float]
    deductible: Optional[float]
    aliases: List[str]


class SQLiteInsuranceMatcher(InsuranceMatcher):
    """Simple alias-based lookup built on top of the seed SQLite database."""

    def __init__(self, config: SQLiteConfig) -> None:
        self._config = config
        self._cache: Optional[List[InsurancePlanRecord]] = None

    async def match(self, name: str) -> Optional[InsuranceMatch]:
        return await asyncio.to_thread(self._match_sync, name)

    async def suggest(self, prefix: str) -> List[InsuranceMatch]:
        return await asyncio.to_thread(self._suggest_sync, prefix)

    def _load_plans(self) -> List[InsurancePlanRecord]:
        if self._cache is not None:
            return self._cache

        with sqlite3.connect(self._config.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT plan_id, payer_name, network_id, coverage_percent, deductible, aliases FROM insurance_plans"
            )
            rows = cursor.fetchall()

        plans: List[InsurancePlanRecord] = []
        for plan_id, payer_name, network_id, coverage_percent, deductible, aliases in rows:
            alias_list = [alias.strip() for alias in (aliases or "").split("|") if alias.strip()]
            plans.append(
                InsurancePlanRecord(
                    plan_id=plan_id,
                    payer_name=payer_name,
                    network_id=network_id,
                    coverage_percent=coverage_percent,
                    deductible=deductible,
                    aliases=alias_list,
                )
            )
        self._cache = plans
        return plans

    def _match_sync(self, name: str) -> Optional[InsuranceMatch]:
        normalized = name.strip().casefold()
        if not normalized:
            return None

        best: Optional[InsuranceMatch] = None
        for plan in self._load_plans():
            score = self._score_plan(plan, normalized)
            if score <= 0:
                continue
            candidate = InsuranceMatch(
                plan_id=plan.plan_id,
                payer_name=plan.payer_name,
                network_id=plan.network_id,
                coverage_percent=plan.coverage_percent,
                deductible=plan.deductible,
                match_score=score,
            )
            if best is None or candidate.match_score > best.match_score:
                best = candidate
        return best

    def _suggest_sync(self, prefix: str) -> List[InsuranceMatch]:
        normalized = prefix.strip().casefold()
        if not normalized:
            return []
        matches: List[InsuranceMatch] = []
        for plan in self._load_plans():
            score = self._score_plan(plan, normalized, prefix_match=True)
            if score <= 0:
                continue
            matches.append(
                InsuranceMatch(
                    plan_id=plan.plan_id,
                    payer_name=plan.payer_name,
                    network_id=plan.network_id,
                    coverage_percent=plan.coverage_percent,
                    deductible=plan.deductible,
                    match_score=score,
                )
            )
        matches.sort(key=lambda item: item.match_score, reverse=True)
        return matches[:5]

    def _score_plan(
        self,
        plan: InsurancePlanRecord,
        normalized_name: str,
        prefix_match: bool = False,
    ) -> float:
        primary = plan.payer_name.casefold()
        alias_matches = [alias.casefold() for alias in plan.aliases]
        candidates = [primary, *alias_matches]
        best_score = 0.0
        for candidate in candidates:
            if not candidate:
                continue
            if candidate == normalized_name:
                return 1.0
            if prefix_match and candidate.startswith(normalized_name):
                best_score = max(best_score, 0.7)
            if normalized_name in candidate or candidate in normalized_name:
                best_score = max(best_score, 0.6)
        return best_score


class StubInsuranceMatcher(InsuranceMatcher):
    def __init__(self) -> None:
        self._plans = [
            InsuranceMatch(
                plan_id="bcbs-mock",
                payer_name="Blue Cross Blue Shield",
                network_id="BCBS",
                coverage_percent=0.8,
                deductible=1500.0,
                match_score=1.0,
            )
        ]

    async def match(self, name: str) -> Optional[InsuranceMatch]:
        normalized = name.strip().casefold()
        if not normalized:
            return None
        for plan in self._plans:
            if plan.payer_name.casefold() in normalized or normalized in plan.payer_name.casefold():
                return plan
        return None

    async def suggest(self, prefix: str) -> List[InsuranceMatch]:
        normalized = prefix.strip().casefold()
        if not normalized:
            return []
        return [plan for plan in self._plans if plan.payer_name.casefold().startswith(normalized)]
