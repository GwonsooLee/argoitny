import React, { useState, useEffect } from 'react';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

const PlanSelector = ({ onSelectPlan, selectedPlan = 'Free', showComingSoon = true, showConfirmButton = false }) => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentSelectedPlan, setCurrentSelectedPlan] = useState(selectedPlan);

  useEffect(() => {
    fetchPlans();
  }, []);

  useEffect(() => {
    setCurrentSelectedPlan(selectedPlan);
  }, [selectedPlan]);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await apiGet(API_ENDPOINTS.availablePlans);

      if (!response.ok) {
        throw new Error('Failed to fetch plans');
      }

      const data = await response.json();
      setPlans(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch plans:', err);
      setError('Failed to load subscription plans');
    } finally {
      setLoading(false);
    }
  };

  // Check if plan is coming soon (Pro or Pro+)
  const isComingSoon = (planName) => {
    return showComingSoon && (planName === 'Pro' || planName === 'Pro+');
  };

  const handlePlanClick = (planName) => {
    if (isComingSoon(planName)) return;

    setCurrentSelectedPlan(planName);

    // If no confirm button, select immediately
    if (!showConfirmButton) {
      onSelectPlan(planName);
    }
  };

  const handleConfirm = () => {
    onSelectPlan(currentSelectedPlan);
  };

  if (loading) {
    return (
      <div className="plan-selector loading">
        <p>Loading plans...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="plan-selector error">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="plan-selector">
      <div className="plans-grid">
        {plans.map((plan) => {
          const comingSoon = isComingSoon(plan.name);
          return (
            <div
              key={plan.id}
              className={`plan-card ${currentSelectedPlan === plan.name ? 'selected' : ''} ${comingSoon ? 'disabled' : ''}`}
              onClick={() => handlePlanClick(plan.name)}
            >
              <div className="plan-header">
                <h4>{plan.name}</h4>
                {comingSoon && <span className="badge coming-soon-badge">Coming Soon</span>}
                {currentSelectedPlan === plan.name && !comingSoon && <span className="badge selected-badge">Selected</span>}
              </div>
            <p className="plan-description">{plan.description}</p>
            <div className="plan-features">
              <ul>
                <li>
                  <strong>Hints:</strong>{' '}
                  {plan.max_hints_per_day === -1 ? 'Unlimited' : `${plan.max_hints_per_day} per day`}
                </li>
                <li>
                  <strong>Executions:</strong>{' '}
                  {plan.max_executions_per_day === -1 ? 'Unlimited' : `${plan.max_executions_per_day} per day`}
                </li>
                <li>
                  <strong>Problems:</strong>{' '}
                  {plan.max_problems === -1 ? 'Unlimited' : plan.max_problems}
                </li>
                {plan.can_register_problems && (
                  <li>
                    <strong>✓</strong> Can register new problems
                  </li>
                )}
              </ul>
            </div>
          </div>
          );
        })}
      </div>
      {showConfirmButton && (
        <div className="confirm-button-container">
          <button
            className="confirm-button"
            onClick={handleConfirm}
            disabled={!currentSelectedPlan}
          >
            Confirm Selection
          </button>
        </div>
      )}
      <style>{`
        .plan-selector {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .plans-grid {
          display: flex;
          flex-direction: row;
          gap: 20px;
          justify-content: center;
          align-items: stretch;
        }

        .plan-card {
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          padding: 20px;
          cursor: pointer;
          transition: all 0.3s ease;
          background: white;
          flex: 1;
          max-width: 300px;
          min-width: 250px;
        }

        .plan-card:hover:not(.disabled) {
          border-color: #4285f4;
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);
          transform: translateY(-2px);
        }

        .plan-card.selected {
          border-color: #4285f4;
          background: #f0f7ff;
        }

        .plan-card.disabled {
          opacity: 0.6;
          cursor: not-allowed;
          background: #f5f5f5;
        }

        .plan-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
        }

        .plan-header h4 {
          margin: 0;
          font-size: 20px;
          color: #333;
        }

        .badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
        }

        .coming-soon-badge {
          background: #ffa726;
          color: white;
        }

        .selected-badge {
          background: #4285f4;
          color: white;
        }

        .plan-description {
          color: #666;
          margin-bottom: 15px;
          min-height: 40px;
        }

        .plan-features ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .plan-features li {
          padding: 8px 0;
          color: #555;
          border-top: 1px solid #e0e0e0;
        }

        .plan-features li:first-child {
          border-top: none;
        }

        .plan-features strong {
          color: #333;
        }

        .loading,
        .error {
          text-align: center;
          padding: 40px;
          color: #666;
        }

        .error {
          color: #d32f2f;
        }

        .confirm-button-container {
          display: flex;
          justify-content: center;
          margin-top: 30px;
        }

        .confirm-button {
          background: #4285f4;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 12px 40px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .confirm-button:hover:not(:disabled) {
          background: #357ae8;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.4);
        }

        .confirm-button:disabled {
          background: #ccc;
          cursor: not-allowed;
          opacity: 0.6;
        }
      `}</style>
    </div>
  );
};

export default PlanSelector;
