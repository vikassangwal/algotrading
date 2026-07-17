import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

def d1(S, K, T, r, sigma):
    return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

def d2(S, K, T, r, sigma):
    return d1(S, K, T, r, sigma) - sigma * np.sqrt(T)

def bs_call_price(S, K, T, r, sigma):
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)
    return S * norm.cdf(_d1) - K * np.exp(-r * T) * norm.cdf(_d2)

def bs_put_price(S, K, T, r, sigma):
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)
    return K * np.exp(-r * T) * norm.cdf(-_d2) - S * norm.cdf(-_d1)

def bs_price(S, K, T, r, sigma, option_type='c'):
    if option_type.lower() == 'c':
        return bs_call_price(S, K, T, r, sigma)
    elif option_type.lower() == 'p':
        return bs_put_price(S, K, T, r, sigma)
    else:
        raise ValueError("Invalid option type. Use 'c' for call or 'p' for put.")

def calculate_greeks(S, K, T, r, sigma, option_type='c'):
    """
    Calculate Greeks (Delta, Gamma, Theta, Vega, Rho) using Black-Scholes.
    """
    _d1 = d1(S, K, T, r, sigma)
    _d2 = d2(S, K, T, r, sigma)
    
    # Delta
    if option_type.lower() == 'c':
        delta = norm.cdf(_d1)
    else:
        delta = norm.cdf(_d1) - 1
        
    # Gamma
    gamma = norm.pdf(_d1) / (S * sigma * np.sqrt(T))
    
    # Theta
    term1 = -(S * norm.pdf(_d1) * sigma) / (2 * np.sqrt(T))
    if option_type.lower() == 'c':
        theta = term1 - r * K * np.exp(-r * T) * norm.cdf(_d2)
    else:
        theta = term1 + r * K * np.exp(-r * T) * norm.cdf(-_d2)
        
    # Vega (usually divided by 100 to get change per 1% change in volatility)
    vega = S * norm.pdf(_d1) * np.sqrt(T)
    
    # Rho (usually divided by 100 to get change per 1% change in interest rate)
    if option_type.lower() == 'c':
        rho = K * T * np.exp(-r * T) * norm.cdf(_d2)
    else:
        rho = -K * T * np.exp(-r * T) * norm.cdf(-_d2)
        
    return {
        'delta': delta,
        'gamma': gamma,
        'theta': theta / 365, # per day
        'vega': vega / 100,   # per 1%
        'rho': rho / 100      # per 1%
    }

def implied_volatility(price, S, K, T, r, option_type='c'):
    """
    Calculate Implied Volatility using Brent's method.
    """
    def objective_function(sigma):
        return bs_price(S, K, T, r, sigma, option_type) - price
        
    try:
        # Volatility should be bounded, typically between 0 and a reasonable upper bound
        iv = brentq(objective_function, 1e-6, 5.0)
        return iv
    except (ValueError, RuntimeError):
        return np.nan
