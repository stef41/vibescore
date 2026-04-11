"""Tests for Bayesian scoring model."""

from __future__ import annotations

import math

import pytest

from vibescore.bayesian import (
    BayesianReport,
    BetaPrior,
    DimensionScore,
    bayesian_grade,
    compute_bayesian_score,
    DEFAULT_PRIORS,
)


class TestBetaPrior:
    def test_mean(self):
        p = BetaPrior(alpha=3.0, beta=7.0)
        assert p.mean == pytest.approx(0.3, abs=0.01)

    def test_mean_uniform(self):
        p = BetaPrior(alpha=1.0, beta=1.0)
        assert p.mean == pytest.approx(0.5)

    def test_variance(self):
        p = BetaPrior(alpha=3.0, beta=7.0)
        assert p.variance > 0
        assert p.variance < 0.25  # Maximum variance for Beta is 0.25

    def test_std(self):
        p = BetaPrior(alpha=10.0, beta=10.0)
        assert p.std == pytest.approx(math.sqrt(p.variance))

    def test_credible_interval(self):
        p = BetaPrior(alpha=50.0, beta=50.0)
        lo, hi = p.credible_interval(0.95)
        assert lo < p.mean < hi
        assert lo >= 0.0
        assert hi <= 1.0

    def test_update(self):
        p = BetaPrior(alpha=2.0, beta=2.0)
        q = p.update(8.0, 2.0)
        assert q.alpha == 10.0
        assert q.beta == 4.0
        assert q.mean > p.mean

    def test_update_shifts_mean(self):
        prior = BetaPrior(alpha=2.0, beta=8.0)  # mean = 0.2
        posterior = prior.update(50.0, 10.0)
        # Strong evidence for high rate → mean shifts up
        assert posterior.mean > 0.7

    def test_pdf_positive(self):
        p = BetaPrior(alpha=2.0, beta=5.0)
        assert p.pdf(0.3) > 0
        assert p.pdf(0.0) == 0.0
        assert p.pdf(1.0) == 0.0

    def test_pdf_mode(self):
        # Mode of Beta(5, 5) is at 0.5
        p = BetaPrior(alpha=5.0, beta=5.0)
        assert p.pdf(0.5) > p.pdf(0.2)
        assert p.pdf(0.5) > p.pdf(0.8)

    def test_kl_divergence_same(self):
        p = BetaPrior(alpha=5.0, beta=5.0)
        assert p.kl_divergence(p) == pytest.approx(0.0, abs=1e-6)

    def test_kl_divergence_different(self):
        p = BetaPrior(alpha=5.0, beta=5.0)
        q = BetaPrior(alpha=2.0, beta=8.0)
        kl = p.kl_divergence(q)
        assert kl > 0

    def test_kl_asymmetric(self):
        p = BetaPrior(alpha=2.0, beta=8.0)
        q = BetaPrior(alpha=5.0, beta=3.0)
        assert abs(p.kl_divergence(q) - q.kl_divergence(p)) > 0.01  # KL is not symmetric


class TestComputeBayesianScore:
    def test_basic(self):
        obs = {"testing": (8, 2), "docs": (6, 4)}
        result = compute_bayesian_score(obs)
        assert isinstance(result, BayesianReport)
        assert len(result.dimensions) == 2
        assert 0.0 < result.overall_score < 1.0

    def test_strong_evidence(self):
        obs = {"testing": (95, 5)}
        result = compute_bayesian_score(obs)
        # Strong evidence for high testing → score near 0.9
        dim = result.dimensions[0]
        assert dim.bayesian_score > 0.8

    def test_weak_evidence_shrinks(self):
        obs = {"testing": (1, 0)}  # Only 1 observation
        result = compute_bayesian_score(obs)
        dim = result.dimensions[0]
        # With prior mean ~0.43, 1 success should not push to 1.0
        assert dim.bayesian_score < 0.7

    def test_shrinkage_positive(self):
        obs = {"testing": (10, 0)}  # All success
        result = compute_bayesian_score(obs)
        dim = result.dimensions[0]
        # Bayesian score < 1.0 due to prior, so shrinkage > 0
        assert dim.shrinkage > 0

    def test_custom_priors(self):
        obs = {"testing": (5, 5)}
        prior_optimistic = {"testing": BetaPrior(alpha=10.0, beta=1.0)}
        prior_pessimistic = {"testing": BetaPrior(alpha=1.0, beta=10.0)}
        r1 = compute_bayesian_score(obs, priors=prior_optimistic)
        r2 = compute_bayesian_score(obs, priors=prior_pessimistic)
        assert r1.overall_score > r2.overall_score

    def test_weights(self):
        obs = {"testing": (9, 1), "docs": (1, 9)}
        w1 = {"testing": 10.0, "docs": 1.0}  # testing weighted high
        w2 = {"testing": 1.0, "docs": 10.0}  # docs weighted high
        r1 = compute_bayesian_score(obs, weights=w1)
        r2 = compute_bayesian_score(obs, weights=w2)
        assert r1.overall_score > r2.overall_score

    def test_credible_interval_contains_mean(self):
        obs = {"testing": (10, 5), "security": (15, 2)}
        result = compute_bayesian_score(obs)
        lo, hi = result.overall_ci
        assert lo <= result.overall_score <= hi

    def test_kl_from_prior_positive(self):
        obs = {"testing": (50, 5)}
        result = compute_bayesian_score(obs)
        assert result.kl_from_prior > 0

    def test_all_defaults(self):
        obs = {dim: (5, 5) for dim in DEFAULT_PRIORS}
        result = compute_bayesian_score(obs)
        assert len(result.dimensions) == len(DEFAULT_PRIORS)

    def test_empty_observations(self):
        result = compute_bayesian_score({})
        assert result.overall_score == 0.0 or len(result.dimensions) == 0


class TestBayesianGrade:
    def test_a_plus(self):
        assert bayesian_grade(0.95) == "A+"

    def test_b(self):
        assert bayesian_grade(0.70) == "B"

    def test_f(self):
        assert bayesian_grade(0.10) == "F"

    def test_boundary_d(self):
        assert bayesian_grade(0.40) == "D"

    def test_c_minus(self):
        assert bayesian_grade(0.50) == "C-"
