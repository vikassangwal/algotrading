import React, { useState } from 'react';

const LegalPages = () => {
  const [activeTab, setActiveTab] = useState('terms');

  const renderContent = () => {
    switch (activeTab) {
      case 'terms':
        return (
          <div className="animate-fadeIn">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Terms & Conditions</h2>
            <p className="mb-4 text-gray-600 leading-relaxed">
              Welcome to our platform. By accessing or using our services, you agree to be bound by these Terms and Conditions.
            </p>
            <h3 className="text-xl font-semibold mb-2 text-gray-800 mt-6">1. User Account</h3>
            <p className="mb-4 text-gray-600 leading-relaxed">
              You are responsible for safeguarding the password that you use to access the service and for any activities or actions under your password.
            </p>
            <h3 className="text-xl font-semibold mb-2 text-gray-800 mt-6">2. Acceptable Use</h3>
            <p className="mb-4 text-gray-600 leading-relaxed">
              You agree not to use the platform in any way that causes, or may cause, damage to the platform or impairment of the availability or accessibility of the platform.
            </p>
          </div>
        );
      case 'privacy':
        return (
          <div className="animate-fadeIn">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Privacy Policy</h2>
            <p className="mb-4 text-gray-600 leading-relaxed">
              Your privacy is important to us. It is our policy to respect your privacy regarding any information we may collect from you across our website.
            </p>
            <h3 className="text-xl font-semibold mb-2 text-gray-800 mt-6">Information We Collect</h3>
            <p className="mb-4 text-gray-600 leading-relaxed">
              We only ask for personal information when we truly need it to provide a service to you. We collect it by fair and lawful means, with your knowledge and consent.
            </p>
          </div>
        );
      case 'risk':
        return (
          <div className="animate-fadeIn">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Risk Disclosure</h2>
            <p className="mb-4 text-gray-600 leading-relaxed">
              Trading in financial markets involves a high degree of risk and may not be suitable for all investors.
            </p>
            <p className="mb-4 text-gray-600 leading-relaxed">
              Before deciding to trade, you should carefully consider your investment objectives, level of experience, and risk appetite. There is a possibility that you may sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose.
            </p>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 md:p-8 bg-white rounded-xl shadow-lg mt-10 border border-gray-100">
      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-4 mb-6">
        <button
          className={`px-5 py-2.5 text-sm font-medium rounded-lg transition-colors duration-200 ${
            activeTab === 'terms' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'bg-gray-50 text-gray-600 hover:bg-gray-100 hover:text-gray-900'
          }`}
          onClick={() => setActiveTab('terms')}
        >
          Terms & Conditions
        </button>
        <button
          className={`px-5 py-2.5 text-sm font-medium rounded-lg transition-colors duration-200 ${
            activeTab === 'privacy' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'bg-gray-50 text-gray-600 hover:bg-gray-100 hover:text-gray-900'
          }`}
          onClick={() => setActiveTab('privacy')}
        >
          Privacy Policy
        </button>
        <button
          className={`px-5 py-2.5 text-sm font-medium rounded-lg transition-colors duration-200 ${
            activeTab === 'risk' 
              ? 'bg-blue-600 text-white shadow-md' 
              : 'bg-gray-50 text-gray-600 hover:bg-gray-100 hover:text-gray-900'
          }`}
          onClick={() => setActiveTab('risk')}
        >
          Risk Disclosure
        </button>
      </div>
      <div className="min-h-[300px]">
        {renderContent()}
      </div>
    </div>
  );
};

export default LegalPages;
