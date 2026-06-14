import numpy as np
from scipy.stats import poisson

class DemandPredictor:
    def __init__(self, critical_threshold: float = 0.80):
        """
        Initialize the Advanced Demand Predictor.
        :param critical_threshold: The probability threshold (e.g., 0.80) to flag an active SINK.
        """
        self.critical_threshold = critical_threshold

    def calculate_stockout_probability(self, hourly_lambda: float, current_stock: int, lookahead_minutes: float = 15.0) -> float:
        """
        Calculates the probability that demand exceeds current stock over an arbitrary lookahead window.
        Uses the Poisson Cumulative Distribution Function (CDF).
        """
        if current_stock <= 0:
            return 1.0
        
        # Scale the hourly arrival rate (lambda) to match our lookahead window
        # E.g., if hourly lambda is 24, a 15-minute window means lambda_scaled = 24 * (15/60) = 6.0
        time_fraction = lookahead_minutes / 60.0
        lambda_scaled = hourly_lambda * time_fraction

        # Probability of getting <= current_stock orders is poisson.cdf
        # Probability of a stockout (demand > current_stock) is 1 - CDF
        prob_no_stockout = poisson.cdf(current_stock, lambda_scaled)
        prob_stockout = 1.0 - prob_no_stockout
        
        return float(prob_stockout)

    def evaluate_node(self, store_id: str, hourly_lambda: float, current_stock: int) -> dict:
        """
        Evaluates a dark store node's risk profile across two distinct horizons:
        1. Immediate Crisis Window (15 mins) -> Determines SINK status
        2. Anticipatory Window (30 mins) -> Prepares GHOST paths before a crisis hits
        """
        # Horizon 1: Immediate risk (Next 15 minutes)
        prob_stockout_15m = self.calculate_stockout_probability(hourly_lambda, current_stock, lookahead_minutes=15.0)
        
        # Horizon 2: Anticipatory risk (Next 30 minutes)
        prob_stockout_30m = self.calculate_stockout_probability(hourly_lambda, current_stock, lookahead_minutes=30.0)
        
        status = "HEALTHY"
        
        # If 15-minute risk is past our critical threshold, it is a desperate SINK
        if prob_stockout_15m >= self.critical_threshold:
            status = "SINK"
        # If the 15-minute window is safe, but the 30-minute window looks bad, trigger a GHOST state
        elif prob_stockout_30m >= 0.50:
            status = "ANTICIPATORY_RISK"
        # Source condition: Ample supply to sustain demand triple the lookahead average
        elif current_stock > (hourly_lambda * 0.5) and prob_stockout_30m < 0.10:
            status = "SOURCE"
            
        return {
            "status": status,
            "stockout_prob": prob_stockout_15m, # Primary tracking probability
            "anticipatory_prob": prob_stockout_30m
        }