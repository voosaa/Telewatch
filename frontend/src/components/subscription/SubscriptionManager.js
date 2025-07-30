import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Crown, 
  Zap, 
  Shield, 
  CreditCard, 
  Bitcoin, 
  AlertCircle, 
  Check, 
  ArrowRight,
  ExternalLink,
  Loader2
} from 'lucide-react';
import axios from 'axios';

const SubscriptionManager = () => {
  const { currentUser } = useAuth();
  const [organization, setOrganization] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [paymentLoading, setPaymentLoading] = useState('');
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [supportedCurrencies, setSupportedCurrencies] = useState([]);

  // Plan configurations
  const plans = {
    free: {
      name: 'Free',
      price: 0,
      color: 'gray',
      icon: Shield,
      features: [
        'Basic monitoring',
        '1 Telegram account',
        '5 groups monitoring',
        'Basic analytics',
        'Community support'
      ]
    },
    pro: {
      name: 'Pro',
      price: 9.99,
      color: 'blue',
      icon: Zap,
      features: [
        'Advanced monitoring',
        '5 Telegram accounts',
        '50 groups monitoring',
        'Advanced analytics & reports',
        'Message forwarding',
        'Priority support',
        'Real-time notifications'
      ]
    },
    enterprise: {
      name: 'Pro Enterprise',
      price: 19.99,
      color: 'purple',
      icon: Crown,
      features: [
        'Unlimited monitoring',
        'Unlimited Telegram accounts',
        'Unlimited groups monitoring',
        'Enterprise analytics & exports',
        'Advanced message forwarding',
        'White-label options',
        '24/7 dedicated support',
        'Custom integrations',
        'API access'
      ]
    }
  };

  useEffect(() => {
    fetchOrganizationData();
    fetchPaymentHistory();
    fetchSupportedCurrencies();
  }, []);

  const fetchOrganizationData = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_BACKEND_URL}/api/organizations/current`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      setOrganization(response.data);
    } catch (err) {
      setError('Failed to load organization data');
    } finally {
      setLoading(false);
    }
  };

  const fetchSupportedCurrencies = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_BACKEND_URL}/api/crypto/currencies`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      setSupportedCurrencies(response.data.currencies || []);
    } catch (err) {
      console.log('Failed to load supported currencies');
      // Set default currencies as fallback
      setSupportedCurrencies([
        { currency: 'btc', name: 'Bitcoin', network: 'BTC' },
        { currency: 'eth', name: 'Ethereum', network: 'ETH' },
        { currency: 'usdt', name: 'Tether', network: 'ETH' },
        { currency: 'usdc', name: 'USD Coin', network: 'ETH' },
        { currency: 'sol', name: 'Solana', network: 'SOL' }
      ]);
    }
  };

  const fetchPaymentHistory = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_BACKEND_URL}/api/crypto/charges`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      setPaymentHistory(response.data.charges || []);
    } catch (err) {
      console.log('No payment history available');
    }
  };

  const handleCryptoUpgrade = async (planType) => {
    setPaymentLoading(planType);
    setError('');

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/crypto/create-charge`,
        { plan: planType },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      // Redirect to Coinbase Commerce payment page
      window.location.href = response.data.hosted_url;
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create payment. Please try again.');
      setPaymentLoading('');
    }
  };

  const getPlanStatus = (planName) => {
    const currentPlan = organization?.plan || 'free';
    const planHierarchy = { free: 0, pro: 1, enterprise: 2 };
    
    if (planHierarchy[currentPlan] > planHierarchy[planName]) {
      return 'downgrade';
    } else if (planHierarchy[currentPlan] === planHierarchy[planName]) {
      return 'current';
    } else {
      return 'upgrade';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Subscription Plans</h1>
        <p className="mt-2 text-gray-600">
          Upgrade your plan to unlock more powerful monitoring features
        </p>
        
        {organization && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-600" />
              <span className="font-medium text-blue-900">
                Current Plan: {plans[organization.plan || 'free']?.name || 'Free'}
              </span>
            </div>
            {organization.last_payment_date && (
              <p className="text-sm text-blue-700 mt-1">
                Last payment: {formatDate(organization.last_payment_date)}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        {Object.entries(plans).map(([planKey, plan]) => {
          const status = getPlanStatus(planKey);
          const IconComponent = plan.icon;
          const isCurrentPlan = status === 'current';
          const isUpgrade = status === 'upgrade';
          const isDowngrade = status === 'downgrade';

          return (
            <div
              key={planKey}
              className={`relative p-6 rounded-xl border-2 ${
                isCurrentPlan
                  ? 'border-green-500 bg-green-50'
                  : `border-${plan.color}-200 bg-white hover:border-${plan.color}-300`
              } transition-all duration-200 ${
                planKey === 'enterprise' ? 'transform scale-105' : ''
              }`}
            >
              {/* Popular Badge */}
              {planKey === 'enterprise' && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-purple-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Current Plan Badge */}
              {isCurrentPlan && (
                <div className="absolute -top-3 right-4">
                  <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm font-medium">
                    Current
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <IconComponent className={`h-12 w-12 text-${plan.color}-600 mx-auto mb-4`} />
                <h3 className="text-2xl font-bold text-gray-900">{plan.name}</h3>
                <div className="mt-2">
                  <span className="text-4xl font-bold text-gray-900">
                    ${plan.price}
                  </span>
                  {plan.price > 0 && (
                    <span className="text-gray-600">/month</span>
                  )}
                </div>
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                    <span className="text-gray-700 text-sm">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* Action Button */}
              <div className="space-y-3">
                {isCurrentPlan ? (
                  <div className="w-full py-3 px-4 bg-green-100 text-green-800 rounded-lg text-center font-medium">
                    Your Current Plan
                  </div>
                ) : isDowngrade ? (
                  <div className="w-full py-3 px-4 bg-gray-100 text-gray-600 rounded-lg text-center font-medium">
                    Downgrade Not Available
                  </div>
                ) : (
                  <button
                    onClick={() => handleCryptoUpgrade(planKey)}
                    disabled={paymentLoading === planKey}
                    className={`w-full py-3 px-4 bg-${plan.color}-600 hover:bg-${plan.color}-700 text-white rounded-lg font-medium transition-colors duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {paymentLoading === planKey ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Bitcoin className="h-4 w-4" />
                        Pay with Crypto
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Crypto Info */}
              {isUpgrade && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Bitcoin className="h-4 w-4 text-orange-600" />
                    <span className="text-sm font-medium text-gray-900">
                      Supported Cryptocurrencies
                    </span>
                  </div>
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>• Bitcoin (BTC)</div>
                    <div>• Ethereum (ETH)</div>
                    <div>• USDT & USDC</div>
                    <div>• Solana (SOL)</div>
                    <div>• + 100+ more coins</div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Features Comparison */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-8">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-xl font-semibold text-gray-900">Feature Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Feature</th>
                <th className="px-6 py-3 text-center text-sm font-medium text-gray-900">Free</th>
                <th className="px-6 py-3 text-center text-sm font-medium text-gray-900">Pro</th>
                <th className="px-6 py-3 text-center text-sm font-medium text-gray-900">Enterprise</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 text-sm text-gray-900">Telegram Accounts</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">1</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">5</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">Unlimited</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="px-6 py-4 text-sm text-gray-900">Groups Monitoring</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">5</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">50</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">Unlimited</td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm text-gray-900">Advanced Analytics</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">❌</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">✅</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">✅</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="px-6 py-4 text-sm text-gray-900">Message Forwarding</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">❌</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">✅</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">✅</td>
              </tr>
              <tr>
                <td className="px-6 py-4 text-sm text-gray-900">API Access</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">❌</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">❌</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">✅</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="px-6 py-4 text-sm text-gray-900">Support Level</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">Community</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">Priority</td>
                <td className="px-6 py-4 text-center text-sm text-gray-600">24/7 Dedicated</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Payment History */}
      {paymentHistory.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-xl font-semibold text-gray-900">Payment History</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Date</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Plan</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Amount</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">Method</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {paymentHistory.map((payment, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {formatDate(payment.created_at)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 capitalize">
                      {payment.plan}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      ${payment.amount}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                        payment.status === 'confirmed' 
                          ? 'bg-green-100 text-green-800'
                          : payment.status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="flex items-center gap-1">
                        <Bitcoin className="h-4 w-4 text-orange-600" />
                        Cryptocurrency
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info Section */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-blue-50 rounded-xl">
          <div className="flex items-center gap-3 mb-4">
            <Bitcoin className="h-6 w-6 text-blue-600" />
            <h4 className="text-lg font-semibold text-blue-900">Cryptocurrency Payments</h4>
          </div>
          <ul className="space-y-2 text-sm text-blue-800">
            <li>• Instant global payments</li>
            <li>• No intermediary fees</li>
            <li>• Secure blockchain technology</li>
            <li>• Support for 100+ cryptocurrencies</li>
            <li>• Automatic plan activation</li>
          </ul>
        </div>

        <div className="p-6 bg-green-50 rounded-xl">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="h-6 w-6 text-green-600" />
            <h4 className="text-lg font-semibold text-green-900">Security & Privacy</h4>
          </div>
          <ul className="space-y-2 text-sm text-green-800">
            <li>• End-to-end encrypted monitoring</li>
            <li>• No personal data stored</li>
            <li>• GDPR compliant infrastructure</li>
            <li>• Secure payment processing</li>
            <li>• Regular security audits</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionManager;