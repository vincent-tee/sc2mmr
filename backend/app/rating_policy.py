"""Shared, database-free rating rules for ingestion and chronological evaluation."""

import math
from statistics import median

import trueskill

from .config import settings

POLICY_VERSION = "trueskill-decay-v3"


def environment():
    return trueskill.TrueSkill(
        mu=settings.trueskill_mu, sigma=settings.trueskill_sigma,
        beta=settings.trueskill_beta, tau=settings.trueskill_tau,
        draw_probability=settings.trueskill_draw_probability,
    )


def typical_session_gap(times):
    times = sorted(times)
    if len(times) < settings.min_games_for_adaptive_decay:
        return 0.0
    gaps = [(b - a).total_seconds() / 86400 for a, b in zip(times, times[1:])]
    gaps = [gap for gap in gaps if gap >= settings.session_gap_hours / 24]
    return median(gaps) if gaps else 0.0


def decayed_sigma(sigma, days, total_games, typical_gap=0.0):
    if days <= 0:
        return sigma
    rate = 0.0833
    if (settings.adaptive_decay_enabled
            and total_games >= settings.min_games_for_adaptive_decay
            and typical_gap > 0):
        days = max(0, days - typical_gap * settings.adaptive_decay_multiplier)
        rate *= min(1.0, 7.0 / typical_gap)
    return min(sigma + rate * days, settings.trueskill_sigma)


def win_probability(team1, team2, *, variance_scale=None):
    if not team1 or not team2:
        raise ValueError("Both teams must contain players")
    delta = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    scale = settings.win_probability_variance_scale if variance_scale is None else variance_scale
    variance = sum(r.sigma ** 2 for r in team1 + team2) * (1 + scale)
    return 0.5 * (1 + math.erf(delta / math.sqrt(2 * variance)))


def rate_teams(team1, team2, team1_won):
    return environment().rate([team1, team2], ranks=[0, 1] if team1_won else [1, 0])
