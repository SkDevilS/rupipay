// Get API base URL from environment variable
const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'}/merchant`;
const API_ROOT = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

class ClientAPI {
  constructor() {
    this.token = localStorage.getItem('merchantToken');
  }

  // Set authorization header
  getHeaders(includeAuth = false) {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (includeAuth && this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    return headers;
  }

  // Handle API response
  async handleResponse(response) {
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || 'API request failed');
    }
    
    return data;
  }

  // Get CAPTCHA
  async getCaptcha() {
    try {
      const response = await fetch(`${API_BASE_URL}/captcha`, {
        method: 'GET',
        headers: this.getHeaders(),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get captcha error:', error);
      throw error;
    }
  }

  // Merchant Login
  async login(merchantId, password) {
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          merchantId,
          password
        }),
      });
      
      const data = await this.handleResponse(response);
      
      if (data.success && data.token) {
        // Store token
        this.token = data.token;
        localStorage.setItem('merchantToken', data.token);
        localStorage.setItem('merchantId', data.merchantId);
        localStorage.setItem('merchantName', data.merchantName);
        localStorage.setItem('isAuthenticated', 'true');
      }
      
      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  // Verify Token
  async verifyToken() {
    try {
      const response = await fetch(`${API_BASE_URL}/verify`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      const data = await this.handleResponse(response);
      
      // Update token if new one is provided
      if (data.success && data.token) {
        this.token = data.token;
        localStorage.setItem('merchantToken', data.token);
      }
      
      return data;
    } catch (error) {
      console.error('Verify token error:', error);
      // Clear invalid token
      this.logout();
      throw error;
    }
  }

  // Merchant Logout
  logout() {
    // Clear local storage
    this.token = null;
    localStorage.removeItem('merchantToken');
    localStorage.removeItem('merchantId');
    localStorage.removeItem('merchantName');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('hasPinSet');
  }

  // Get Credentials
  async getCredentials() {
    try {
      const response = await fetch(`${API_BASE_URL}/credentials`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get credentials error:', error);
      throw error;
    }
  }

  // Add IP to Whitelist
  async addIpWhitelist(ipAddress) {
    try {
      const response = await fetch(`${API_BASE_URL}/ip-whitelist`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ ipAddress }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Add IP whitelist error:', error);
      throw error;
    }
  }

  // Remove IP from Whitelist
  async removeIpWhitelist(ipAddress) {
    try {
      const response = await fetch(`${API_BASE_URL}/ip-whitelist/${encodeURIComponent(ipAddress)}`, {
        method: 'DELETE',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Remove IP whitelist error:', error);
      throw error;
    }
  }

  // Update Callback URLs
  async updateCallbacks(payinCallbackUrl, payoutCallbackUrl) {
    try {
      const response = await fetch(`${API_BASE_URL}/callbacks`, {
        method: 'PUT',
        headers: this.getHeaders(true),
        body: JSON.stringify({
          payinCallbackUrl,
          payoutCallbackUrl,
        }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Update callbacks error:', error);
      throw error;
    }
  }

  // Get Commercials
  async getCommercials() {
    try {
      const response = await fetch(`${API_BASE_URL}/commercials`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get commercials error:', error);
      throw error;
    }
  }

  // Change Password
  async changePassword(currentPassword, newPassword, confirmPassword) {
    try {
      const response = await fetch(`${API_BASE_URL}/change-password`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ currentPassword, newPassword, confirmPassword }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Change password error:', error);
      throw error;
    }
  }

  // Check PIN Status
  async checkPinStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/pin-status`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Check PIN status error:', error);
      throw error;
    }
  }

  // Change/Set PIN
  async changePin(currentPin, newPin, confirmPin) {
    try {
      const response = await fetch(`${API_BASE_URL}/change-pin`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ currentPin, newPin, confirmPin }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Change PIN error:', error);
      throw error;
    }
  }

  // Verify PIN
  async verifyPin(pin) {
    try {
      const response = await fetch(`${API_BASE_URL}/verify-pin`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ pin }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Verify PIN error:', error);
      throw error;
    }
  }

  // Delete PIN
  async deletePin() {
    try {
      const response = await fetch(`${API_BASE_URL}/delete-pin`, {
        method: 'DELETE',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Delete PIN error:', error);
      throw error;
    }
  }

  // Encrypt Data
  async encryptData(plainText) {
    try {
      const response = await fetch(`${API_BASE_URL}/encrypt`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ plainText }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Encrypt data error:', error);
      throw error;
    }
  }

  // Decrypt Data
  async decryptData(encryptedText) {
    try {
      const response = await fetch(`${API_BASE_URL}/decrypt`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify({ encryptedText }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Decrypt data error:', error);
      throw error;
    }
  }

  // Get Wallet Overview
  async getWalletOverview() {
    try {
      const response = await fetch(`${API_ROOT}/wallet/merchant/overview`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get wallet overview error:', error);
      throw error;
    }
  }

  // Get Wallet Statement
  async getWalletStatement(filters = {}) {
    try {
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`${API_ROOT}/wallet/merchant/statement${queryParams ? '?' + queryParams : ''}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get wallet statement error:', error);
      throw error;
    }
  }

  // Get Payout Report
  async getPayoutReport(filters = {}) {
    try {
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`${API_ROOT}/payout/client/report${queryParams ? '?' + queryParams : ''}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get payout report error:', error);
      throw error;
    }
  }

  async getAllPayoutReport(filters = {}) {
    try {
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`${API_ROOT}/payout/client/report/all${queryParams ? '?' + queryParams : ''}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get all payout report error:', error);
      throw error;
    }
  }

  async getTodayPayoutReport() {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/report/today`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get today payout report error:', error);
      throw error;
    }
  }

  // Sync Payout Status
  async syncPayoutStatus(txnId) {
    try {
      const response = await fetch(`${API_ROOT}/payout/sync-status/${txnId}`, {
        method: 'POST',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Sync payout status error:', error);
      throw error;
    }
  }

  // Get Payout Stats
  async getPayoutStats() {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/stats`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get payout stats error:', error);
      throw error;
    }
  }

  // Get Payin Stats
  async getPayinStats() {
    try {
      const response = await fetch(`${API_ROOT}/payin/stats`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get payin stats error:', error);
      throw error;
    }
  }

  // Get Merchant Banks
  async getBanks() {
    try {
      const response = await fetch(`${API_BASE_URL}/banks`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get banks error:', error);
      throw error;
    }
  }

  // Get Merchant Banks (alias)
  async getMerchantBanks() {
    return this.getBanks();
  }

  // Add Bank
  async addBank(bankData) {
    try {
      const response = await fetch(`${API_BASE_URL}/banks`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify(bankData),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Add bank error:', error);
      throw error;
    }
  }

  // Update Bank
  async updateBank(bankId, bankData) {
    try {
      const response = await fetch(`${API_BASE_URL}/banks/${bankId}`, {
        method: 'PUT',
        headers: this.getHeaders(true),
        body: JSON.stringify(bankData),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Update bank error:', error);
      throw error;
    }
  }

  // Delete Bank
  async deleteBank(bankId, tpin) {
    try {
      const response = await fetch(`${API_BASE_URL}/banks/${bankId}`, {
        method: 'DELETE',
        headers: this.getHeaders(true),
        body: JSON.stringify({ tpin }),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Delete bank error:', error);
      throw error;
    }
  }

  // Toggle Bank Status
  async toggleBankStatus(bankId) {
    try {
      const response = await fetch(`${API_BASE_URL}/banks/${bankId}/toggle-status`, {
        method: 'PUT',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Toggle bank status error:', error);
      throw error;
    }
  }

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.token && localStorage.getItem('isAuthenticated') === 'true';
  }

  // Get current merchant ID
  getMerchantId() {
    return localStorage.getItem('merchantId');
  }

  // Get merchant name
  getMerchantName() {
    return localStorage.getItem('merchantName');
  }

  // Payin APIs
  async createPayinOrder(orderData) {
    try {
      const response = await fetch(`${API_ROOT}/payin/order/create`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify(orderData),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Create payin order error:', error);
      throw error;
    }
  }

  // Mudrape Payin APIs
  async createMudrapeOrder(orderData) {
    try {
      const response = await fetch(`${API_ROOT}/mudrape/order/create`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify(orderData),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Create Mudrape order error:', error);
      throw error;
    }
  }

  async getMudrapeStatus(txnId) {
    try {
      const response = await fetch(`${API_ROOT}/mudrape/status/${txnId}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get Mudrape status error:', error);
      throw error;
    }
  }

  async getMudrapeStatusByOrderId(orderId) {
    try {
      const response = await fetch(`${API_ROOT}/mudrape/status/order/${orderId}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get Mudrape status by order ID error:', error);
      throw error;
    }
  }

  async getMerchantGateway(serviceType = 'PAYIN') {
    try {
      const merchantId = this.getMerchantId();
      const response = await fetch(`${API_ROOT}/routing/merchant/${merchantId}/gateway?service_type=${serviceType}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get merchant gateway error:', error);
      throw error;
    }
  }

  async getPayinStatus(txnId) {
    try {
      const response = await fetch(`${API_ROOT}/payin/status/${txnId}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get payin status error:', error);
      throw error;
    }
  }

  async getPayinTransactions(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const response = await fetch(`${API_ROOT}/payin/transactions?${queryString}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get payin transactions error:', error);
      throw error;
    }
  }

  async getAllPayinTransactions(params = {}) {
    try {
      const queryString = new URLSearchParams(params).toString();
      const response = await fetch(`${API_ROOT}/payin/transactions/all?${queryString}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get all payin transactions error:', error);
      throw error;
    }
  }

  async getTodayPayinTransactions() {
    try {
      const response = await fetch(`${API_ROOT}/payin/transactions/today`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get today payin transactions error:', error);
      throw error;
    }
  }

  // Fund Request APIs
  async createFundRequest(requestData) {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/fund-request`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify(requestData),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Create fund request error:', error);
      throw error;
    }
  }

  async getFundRequests() {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/fund-requests`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get fund requests error:', error);
      throw error;
    }
  }

  async settleFund(settleData) {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/settle-fund`, {
        method: 'POST',
        headers: this.getHeaders(true),
        body: JSON.stringify(settleData),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Settle fund error:', error);
      throw error;
    }
  }

  async getClientWalletStatement(filters = {}) {
    try {
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`${API_ROOT}/payout/client/wallet-statement?${queryParams}`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get client wallet statement error:', error);
      throw error;
    }
  }

  async getUnsettledWalletBalance() {
    try {
      const response = await fetch(`${API_ROOT}/payout/client/unsettled-wallet`, {
        method: 'GET',
        headers: this.getHeaders(true),
      });
      return await this.handleResponse(response);
    } catch (error) {
      console.error('Get unsettled wallet balance error:', error);
      throw error;
    }
  }

  // Get Merchant Banks (alias for compatibility)
  async getMerchantBanks() {
    return this.getBanks();
  }
}

// Create singleton instance
const clientAPI = new ClientAPI();

// Export both named and default
export { clientAPI };
export default clientAPI;

