"""Bayesian estimation for two groups

This module implements Bayesian estimation for two groups, providing
complete distributions for effect size, group means and their
difference, standard deviations and their difference, and the
normality of the data.

Based on:

Kruschke, J. (2012) Bayesian estimation supersedes the t
    test. Journal of Experimental Psychology: General.

"""

import pymc3 as pm
import numpy as np
import scipy.stats


def make_model(data: dict):
    assert len(data) == 2, 'There must be exactly two data arrays'

    name1, name2 = sorted(data.keys())

    y1 = np.array(data[name1])
    y2 = np.array(data[name2])

    assert y1.ndim == 1
    assert y2.ndim == 1
    y = np.concatenate((y1, y2))

    mu_m = np.mean(y)
    mu_scale = np.std(y) * 1000

    sigma_low = np.std(y) / 1000
    sigma_high = np.std(y) * 1000

    with pm.Model() as model:
        # the five prior distributions for the parameters in our model
        group1_mean = pm.Normal('group1_mean', mu=mu_m, sd=mu_scale)
        group2_mean = pm.Normal('group2_mean', mu=mu_m, sd=mu_scale)
        group1_std = pm.Uniform('group1_std', lower=sigma_low, upper=sigma_high)
        group2_std = pm.Uniform('group2_std', lower=sigma_low, upper=sigma_high)
        lambda_1 = group1_std ** (-2)
        lambda_2 = group2_std ** (-2)
        nu = pm.Exponential('nu_minus_one', 1 / 29.) + 1
        _ = pm.StudentT(name1, observed=y1,
                        nu=nu, mu=group1_mean, lam=lambda_1)
        _ = pm.StudentT(name2, observed=y2,
                        nu=nu, mu=group2_mean, lam=lambda_2)

    return model


def hdi_of_mcmc(sample_vec, cred_mass=0.95):
    assert len(sample_vec), 'need points to find HDI'
    sorted_pts = np.sort(sample_vec)

    ci_idx_inc = int(np.floor(cred_mass * len(sorted_pts)))
    n_cis = len(sorted_pts) - ci_idx_inc
    ci_width = sorted_pts[ci_idx_inc:] - sorted_pts[:n_cis]

    min_idx = np.argmin(ci_width)
    hdi_min = sorted_pts[min_idx]
    hdi_max = sorted_pts[min_idx + ci_idx_inc]
    return hdi_min, hdi_max


def calculate_sample_statistics(sample_vec):
    hdi_min, hdi_max = hdi_of_mcmc(sample_vec)

    # calculate mean
    mean_val = np.mean(sample_vec)

    # calculate mode (use kernel density estimate)
    kernel = scipy.stats.gaussian_kde(sample_vec)
    if 1:
        # (Could we use the mean shift algorithm instead of this?)
        bw = kernel.covariance_factor()
        cut = 3 * bw
        xlow = np.min(sample_vec) - cut * bw
        xhigh = np.max(sample_vec) + cut * bw
        n = 512
        x = np.linspace(xlow, xhigh, n)
        vals = kernel.evaluate(x)
        max_idx = np.argmax(vals)
        mode_val = x[max_idx]
    return {'hdi_min': hdi_min,
            'hdi_max': hdi_max,
            'mean': mean_val,
            'mode': mode_val,
            }
