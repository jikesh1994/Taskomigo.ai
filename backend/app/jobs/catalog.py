"""Starter companies with public job boards (each verified live on 2026-09-29).

Offered as one-click suggestions; users can add any other Greenhouse/Lever board.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    platform: str
    board: str
    company: str


CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry("greenhouse", "stripe", "Stripe"),
    CatalogEntry("greenhouse", "airbnb", "Airbnb"),
    CatalogEntry("greenhouse", "figma", "Figma"),
    CatalogEntry("greenhouse", "discord", "Discord"),
    CatalogEntry("greenhouse", "databricks", "Databricks"),
    CatalogEntry("greenhouse", "cloudflare", "Cloudflare"),
    CatalogEntry("greenhouse", "coinbase", "Coinbase"),
    CatalogEntry("greenhouse", "gitlab", "GitLab"),
    CatalogEntry("greenhouse", "reddit", "Reddit"),
    CatalogEntry("greenhouse", "dropbox", "Dropbox"),
    CatalogEntry("greenhouse", "twilio", "Twilio"),
    CatalogEntry("greenhouse", "mongodb", "MongoDB"),
    CatalogEntry("greenhouse", "elastic", "Elastic"),
    CatalogEntry("greenhouse", "groww", "Groww"),
    CatalogEntry("greenhouse", "hackerrank", "HackerRank"),
    CatalogEntry("lever", "palantir", "Palantir"),
    CatalogEntry("lever", "spotify", "Spotify"),
    CatalogEntry("lever", "meesho", "Meesho"),
    CatalogEntry("lever", "cred", "CRED"),
    CatalogEntry("lever", "zeta", "Zeta"),
    CatalogEntry("lever", "fampay", "FamPay"),
)
