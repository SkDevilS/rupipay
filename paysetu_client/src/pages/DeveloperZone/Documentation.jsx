import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Book, Code, Key, Zap, AlertCircle, CheckCircle2, Copy } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

export default function Documentation() {
  const [copiedCode, setCopiedCode] = useState(null)

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(id)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const baseUrl = window.location.origin

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Book className="h-8 w-8 text-orange-600" />
        <div>
          <h1 className="text-3xl font-bold">API Documentation</h1>
          <p className="text-gray-600 mt-1">Complete guide for PayIN and PayOUT integration</p>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full max-w-4xl grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="authentication">Authentication</TabsTrigger>
          <TabsTrigger value="token">Get Token</TabsTrigger>
          <TabsTrigger value="payin">PayIN API</TabsTrigger>
          <TabsTrigger value="payout">PayOUT API</TabsTrigger>
          <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Book className="h-5 w-5" />
                Getting Started
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold mb-3 text-lg">Production API Base URL</h3>
                <div className="relative">
                  <code className="block bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm">
                    https://api.rupipay.shop/api
                  </code>
                  <button
                    onClick={() => copyToClipboard('https://api.rupipay.shop/api', 'base-url')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'base-url' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">What is Paysetu API?</h3>
                <p className="text-gray-600 mb-4">
                  Paysetu provides a comprehensive payment gateway solution for businesses to accept payments (PayIN) 
                  and disburse funds (PayOUT) seamlessly. Our APIs are designed to be simple, secure, and scalable.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4 bg-gradient-to-br from-green-50 to-white">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="h-8 w-8 bg-green-100 rounded-lg flex items-center justify-center">
                        <Zap className="h-5 w-5 text-green-600" />
                      </div>
                      <span className="font-semibold text-green-900">PayIN API</span>
                    </div>
                    <p className="text-sm text-gray-600">
                      Accept payments from customers via UPI, QR codes, payment links, and more. 
                      Real-time payment confirmation with instant settlement.
                    </p>
                  </div>
                  <div className="border rounded-lg p-4 bg-gradient-to-br from-blue-50 to-white">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="h-8 w-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Code className="h-5 w-5 text-blue-600" />
                      </div>
                      <span className="font-semibold text-blue-900">PayOUT API</span>
                    </div>
                    <p className="text-sm text-gray-600">
                      Disburse funds to bank accounts via IMPS, NEFT, or RTGS. 
                      Perfect for vendor payments, refunds, and salary disbursements.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Key Features</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="font-semibold text-sm">Secure Encryption</p>
                      <p className="text-xs text-gray-600">AES-256-CBC encryption for all data</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="font-semibold text-sm">Real-time Webhooks</p>
                      <p className="text-xs text-gray-600">Instant transaction status updates</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="font-semibold text-sm">24x7 Availability</p>
                      <p className="text-xs text-gray-600">IMPS transfers work round the clock</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="font-semibold text-sm">Developer Friendly</p>
                      <p className="text-xs text-gray-600">RESTful APIs with comprehensive docs</p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Response Format</h3>
                <p className="text-gray-600 mb-3">All API responses follow a standard JSON structure:</p>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "message": "Operation successful",
  "data": {
    // Response data here
  }
}`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">HTTP Status Codes</h3>
                <div className="space-y-2">
                  <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                    <span className="font-mono font-semibold text-green-700">200</span>
                    <div>
                      <p className="font-semibold text-green-900">Success</p>
                      <p className="text-sm text-green-700">Request completed successfully</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg">
                    <span className="font-mono font-semibold text-yellow-700">400</span>
                    <div>
                      <p className="font-semibold text-yellow-900">Bad Request</p>
                      <p className="text-sm text-yellow-700">Invalid parameters or missing required fields</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                    <span className="font-mono font-semibold text-red-700">401</span>
                    <div>
                      <p className="font-semibold text-red-900">Unauthorized</p>
                      <p className="text-sm text-red-700">Invalid or missing authentication credentials</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                    <span className="font-mono font-semibold text-red-700">500</span>
                    <div>
                      <p className="font-semibold text-red-900">Server Error</p>
                      <p className="text-sm text-red-700">Internal server error occurred</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-1">Important Notes</h4>
                    <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                      <li>All requests must use HTTPS protocol</li>
                      <li>Request and response payloads are AES-256 encrypted</li>
                      <li>Timestamps are in ISO 8601 format (UTC)</li>
                      <li>Amount values are in INR (Indian Rupees)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="authentication" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Authentication
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold mb-3 text-lg">API Credentials</h3>
                <p className="text-gray-600 mb-4">
                  All API requests require authentication using your Authorization Key and Module Secret. 
                  You can find these credentials in the <a href="/developer/credentials" className="text-orange-600 hover:underline">Credentials</a> section.
                </p>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-yellow-900 mb-1">Security Warning</h4>
                      <p className="text-sm text-yellow-800">
                        Never expose your Module Secret in client-side code or public repositories. 
                        Always make API calls from your secure backend server.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Request Headers</h3>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`X-Authorization-Key: your_authorization_key
X-Module-Secret: your_module_secret
Content-Type: application/json`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard('X-Authorization-Key: your_authorization_key\nX-Module-Secret: your_module_secret\nContent-Type: application/json', 'auth-headers')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'auth-headers' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">AES Encryption</h3>
                <p className="text-gray-600 mb-4">
                  Request and response data must be encrypted using AES-256-CBC encryption with your unique AES Key and IV.
                </p>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold mb-2">Encryption Process</h4>
                    <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                      <li>Convert your JSON payload to string</li>
                      <li>Encrypt the string using AES-256-CBC with your AES Key and IV</li>
                      <li>Base64 encode the encrypted data</li>
                      <li>Send the encoded string in the request body as <code className="bg-gray-100 px-1 rounded">data</code> field</li>
                    </ol>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">Decryption Process</h4>
                    <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                      <li>Extract the <code className="bg-gray-100 px-1 rounded">data</code> field from response</li>
                      <li>Base64 decode the string</li>
                      <li>Decrypt using AES-256-CBC with your AES Key and IV</li>
                      <li>Parse the decrypted string as JSON</li>
                    </ol>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Sample Code (Node.js)</h3>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`const crypto = require('crypto');

// Encryption
function encryptAES(data, key, iv) {
  const cipher = crypto.createCipheriv(
    'aes-256-cbc',
    Buffer.from(key, 'hex'),
    Buffer.from(iv, 'hex')
  );
  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return encrypted;
}

// Decryption
function decryptAES(encryptedData, key, iv) {
  const decipher = crypto.createDecipheriv(
    'aes-256-cbc',
    Buffer.from(key, 'hex'),
    Buffer.from(iv, 'hex')
  );
  let decrypted = decipher.update(encryptedData, 'base64', 'utf8');
  decrypted += decipher.final('utf8');
  return JSON.parse(decrypted);
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`const crypto = require('crypto');\n\n// Encryption\nfunction encryptAES(data, key, iv) {\n  const cipher = crypto.createCipheriv(\n    'aes-256-cbc',\n    Buffer.from(key, 'hex'),\n    Buffer.from(iv, 'hex')\n  );\n  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'base64');\n  encrypted += cipher.final('base64');\n  return encrypted;\n}\n\n// Decryption\nfunction decryptAES(encryptedData, key, iv) {\n  const decipher = crypto.createDecipheriv(\n    'aes-256-cbc',\n    Buffer.from(key, 'hex'),\n    Buffer.from(iv, 'hex')\n  );\n  let decrypted = decipher.update(encryptedData, 'base64', 'utf8');\n  decrypted += decipher.final('utf8');\n  return JSON.parse(decrypted);\n}`, 'aes-code')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'aes-code' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="token" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Get Bearer Token (JWT)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold mb-3 text-lg">Overview</h3>
                <p className="text-gray-600 mb-4">
                  For PayOUT API and wallet operations, you need a Bearer token (JWT). This token authenticates your API requests.
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-1">Token Validity</h4>
                      <p className="text-sm text-blue-800">
                        JWT tokens are valid for 1 hour. After expiration, generate a new token by logging in again.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Simple Login (Recommended)</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST /api/merchant/login</code>
                  </p>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Body</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`POST /api/merchant/login

Request Body:
{
  "merchantId": "your_merchant_id",
  "password": "your_password"
}

Response:
{
  "success": true,
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "merchantId": "your_merchant_id",
  "merchantName": "Your Business Name",
  "email": "your@email.com"
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard('POST /api/merchant/login\n\nRequest Body:\n{\n  "merchantId": "your_merchant_id",\n  "password": "your_password"\n}\n\nResponse:\n{\n  "success": true,\n  "message": "Login successful",\n  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",\n  "merchantId": "your_merchant_id",\n  "merchantName": "Your Business Name",\n  "email": "your@email.com"\n}', 'login-simple')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'login-simple' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Using the Bearer Token</h3>
                <p className="text-gray-600 mb-4">
                  Include the token in the Authorization header for all PayOUT API requests:
                </p>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Sample Code (Node.js)</h3>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`const axios = require('axios');

async function getToken() {
  try {
    const response = await axios.post(
      'https://api.rupipay.shop/api/merchant/login',
      {
        merchantId: 'your_merchant_id',
        password: 'your_password'
      }
    );
    
    const token = response.data.token;
    console.log('Bearer Token:', token);
    return token;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Use the token for API requests
async function makePayoutRequest(token) {
  try {
    const response = await axios.post(
      'https://api.rupipay.shop/api/payout/client/direct-payout',
      {
        order_id: 'MERCHANT_ORDER_12345',
        amount: 1000.00,
        tpin: '1234',
        account_holder_name: 'John Doe',
        account_number: '1234567890',
        ifsc_code: 'SBIN0001234',
        bank_name: 'State Bank of India',
        payment_type: 'IMPS'
      },
      {
        headers: {
          'Authorization': \`Bearer \${token}\`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('Payout Response:', response.data);
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Execute
getToken().then(token => {
  if (token) {
    makePayoutRequest(token);
  }
});`}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payin" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-green-600" />
                PayIN API - Collect Payments
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-gray-600 mb-4">
                  The PayIN API allows you to collect payments from customers via UPI, QR codes, and payment links.
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Create PayIN Order</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST /api/payin/order/create</code>
                  </p>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Headers</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`X-Authorization-Key: your_authorization_key
X-Module-Secret: your_module_secret
Content-Type: application/json`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Body (Before Encryption)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "amount": 1000.00,
  "orderid": "ORDER123456789",
  "payee_fname": "John",
  "payee_lname": "Doe",
  "payee_mobile": "9876543210",
  "payee_email": "customer@example.com",
  "callbackurl": "https://yoursite.com/callback"
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`{\n  "amount": 1000.00,\n  "orderid": "ORDER123456789",\n  "payee_fname": "John",\n  "payee_lname": "Doe",\n  "payee_mobile": "9876543210",\n  "payee_email": "customer@example.com",\n  "callbackurl": "https://yoursite.com/callback"\n}`, 'payin-req')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'payin-req' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Parameters</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="border p-2 text-left">Parameter</th>
                        <th className="border p-2 text-left">Type</th>
                        <th className="border p-2 text-left">Required</th>
                        <th className="border p-2 text-left">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border p-2 font-mono">amount</td>
                        <td className="border p-2">Number</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Transaction amount in INR (min: 10, max: 100000)</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">orderid</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Unique order ID from your system</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">payee_fname</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Customer first name</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">payee_lname</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">Customer last name</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">payee_mobile</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Customer mobile number (10 digits)</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">payee_email</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Customer email address</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">callbackurl</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">Webhook URL for payment status updates</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Actual Request (After Encryption)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "data": "base64_encoded_encrypted_payload"
}`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Success Response (Decrypted)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "message": "Order created successfully",
  "data": {
    "txn_id": "TXN20260216123456ABC",
    "order_id": "ORDER123456789",
    "amount": 1000.00,
    "charge_amount": 20.00,
    "net_amount": 980.00,
    "payment_url": "https://secure.payu.in/...",
    "payment_params": {
      "key": "merchant_key",
      "txnid": "TXN20260216123456ABC",
      "amount": "1000.00",
      "productinfo": "Payment",
      "firstname": "John",
      "email": "customer@example.com",
      "phone": "9876543210",
      "surl": "https://api.rupipay.shop/api/payin/callback/success",
      "furl": "https://api.rupipay.shop/api/payin/callback/failure",
      "hash": "generated_hash"
    }
  }
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`{\n  "success": true,\n  "message": "Order created successfully",\n  "data": {\n    "txn_id": "TXN20260216123456ABC",\n    "order_id": "ORDER123456789",\n    "amount": 1000.00,\n    "charge_amount": 20.00,\n    "net_amount": 980.00,\n    "payment_url": "https://secure.payu.in/...",\n    "payment_params": {...}\n  }\n}`, 'payin-res')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'payin-res' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Error Response</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": false,
  "message": "Invalid amount or missing required fields"
}`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Check Transaction Status</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST /api/payin/transaction/status</code>
                  </p>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Body (Before Encryption)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "txn_id": "TXN20260216123456ABC"
}`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Success Response (Decrypted)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "data": {
    "txn_id": "TXN20260216123456ABC",
    "order_id": "ORDER123456789",
    "amount": 1000.00,
    "charge_amount": 20.00,
    "net_amount": 980.00,
    "status": "SUCCESS",
    "pg_txn_id": "403993715527634917",
    "utr": "UTR123456789",
    "payment_mode": "UPI",
    "created_at": "2026-02-16T10:30:00Z",
    "updated_at": "2026-02-16T10:31:00Z"
  }
}`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Verify Payment (Real-time Status Check)</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST /api/payin/verify-payment</code>
                  </p>
                </div>
                <p className="text-gray-600 mb-4">
                  This endpoint checks the real-time payment status from the payment gateway and automatically credits 
                  your wallet if the payment is successful. Use this to verify payment completion after customer makes payment.
                </p>

                <h4 className="font-semibold mb-2 mt-4">Request Headers</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`Authorization: Bearer your_jwt_token
Content-Type: application/json`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Body (Before Encryption)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "order_id": "ORDER123456789"
}

// OR

{
  "txn_id": "TXN20260216123456ABC"
}`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Success Response (Decrypted)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "message": "Payment verified successfully",
  "data": {
    "txn_id": "TXN20260216123456ABC",
    "order_id": "ORDER123456789",
    "amount": "1000.00",
    "charge_amount": "20.00",
    "net_amount": "980.00",
    "status": "SUCCESS",
    "pg_partner": "Mudrape",
    "pg_txn_id": "MUDRAPE_TXN_123",
    "utr": "UTR123456789",
    "payment_mode": "UPI",
    "payee_name": "John Doe",
    "payee_mobile": "9876543210",
    "payee_email": "customer@example.com",
    "created_at": "2026-02-22T12:34:56Z",
    "completed_at": "2026-02-22T12:35:30Z",
    "message": "Payment verification successful"
  }
}`}
                  </pre>
                </div>

                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
                  <h4 className="font-semibold text-green-900 mb-2">Key Features</h4>
                  <ul className="text-sm text-green-800 space-y-1 list-disc list-inside">
                    <li>Queries payment gateway for real-time status</li>
                    <li>Automatically credits wallet if payment is SUCCESS</li>
                    <li>Returns complete transaction details with timestamps</li>
                    <li>Works with both PayU and Mudrape gateways</li>
                    <li>Use order_id or txn_id to verify payment</li>
                  </ul>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Sample Code (Node.js)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`const axios = require('axios');
const crypto = require('crypto');

const AES_KEY = 'your_aes_key';
const AES_IV = 'your_aes_iv';
const BEARER_TOKEN = 'your_jwt_token';

function encryptAES(data) {
  const cipher = crypto.createCipheriv(
    'aes-256-cbc',
    Buffer.from(AES_KEY, 'hex'),
    Buffer.from(AES_IV, 'hex')
  );
  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return encrypted;
}

function decryptAES(encryptedData) {
  const decipher = crypto.createDecipheriv(
    'aes-256-cbc',
    Buffer.from(AES_KEY, 'hex'),
    Buffer.from(AES_IV, 'hex')
  );
  let decrypted = decipher.update(encryptedData, 'base64', 'utf8');
  decrypted += decipher.final('utf8');
  return JSON.parse(decrypted);
}

async function verifyPayment(orderId) {
  try {
    const requestData = { order_id: orderId };
    const encryptedData = encryptAES(requestData);

    const response = await axios.post(
      'https://api.rupipay.shop/api/payin/verify-payment',
      { data: encryptedData },
      {
        headers: {
          'Authorization': \`Bearer \${BEARER_TOKEN}\`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (response.data.success) {
      const decryptedData = decryptAES(response.data.data);
      console.log('Payment Status:', decryptedData.status);
      console.log('Amount:', decryptedData.amount);
      console.log('UTR:', decryptedData.utr);
      console.log('Completed At:', decryptedData.completed_at);
      return decryptedData;
    }
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// Verify payment by order ID
verifyPayment('ORDER123456789');`}
                  </pre>
                </div>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-900 mb-2">Transaction Status Values</h4>
                <ul className="text-sm text-green-800 space-y-1">
                  <li><code className="bg-green-100 px-2 py-0.5 rounded">PENDING</code> - Payment initiated, awaiting customer action</li>
                  <li><code className="bg-green-100 px-2 py-0.5 rounded">SUCCESS</code> - Payment completed successfully</li>
                  <li><code className="bg-green-100 px-2 py-0.5 rounded">FAILED</code> - Payment failed or declined</li>
                  <li><code className="bg-green-100 px-2 py-0.5 rounded">CANCELLED</code> - Payment cancelled by customer</li>
                </ul>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Sample Integration Code</h3>
                <Tabs defaultValue="nodejs" className="w-full">
                  <TabsList className="grid w-full max-w-md grid-cols-4">
                    <TabsTrigger value="nodejs">Node.js</TabsTrigger>
                    <TabsTrigger value="python">Python</TabsTrigger>
                    <TabsTrigger value="java">Java</TabsTrigger>
                    <TabsTrigger value="dotnet">.NET</TabsTrigger>
                  </TabsList>

                  <TabsContent value="nodejs" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`const axios = require('axios');
const crypto = require('crypto');

const AUTH_KEY = 'your_authorization_key';
const MODULE_SECRET = 'your_module_secret';
const AES_KEY = 'your_aes_key';
const AES_IV = 'your_aes_iv';

function encryptAES(data) {
  const cipher = crypto.createCipheriv(
    'aes-256-cbc',
    Buffer.from(AES_KEY, 'hex'),
    Buffer.from(AES_IV, 'hex')
  );
  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return encrypted;
}

async function createPayinOrder() {
  const orderData = {
    amount: 1000.00,
    orderid: 'ORDER' + Date.now(),
    payee_fname: 'John',
    payee_lname: 'Doe',
    payee_mobile: '9876543210',
    payee_email: 'customer@example.com',
    callbackurl: 'https://yoursite.com/callback'
  };

  const encryptedData = encryptAES(orderData);

  try {
    const response = await axios.post(
      'https://api.rupipay.shop/api/payin/order/create',
      { data: encryptedData },
      {
        headers: {
          'X-Authorization-Key': AUTH_KEY,
          'X-Module-Secret': MODULE_SECRET,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log('Order created:', response.data);
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

createPayinOrder();`}
                      </pre>
                      <button
                        onClick={() => copyToClipboard(`const axios = require('axios');\nconst crypto = require('crypto');\n\nconst AUTH_KEY = 'your_authorization_key';\nconst MODULE_SECRET = 'your_module_secret';\nconst AES_KEY = 'your_aes_key';\nconst AES_IV = 'your_aes_iv';\n\nfunction encryptAES(data) {\n  const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(AES_KEY, 'hex'), Buffer.from(AES_IV, 'hex'));\n  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'base64');\n  encrypted += cipher.final('base64');\n  return encrypted;\n}\n\nasync function createPayinOrder() {\n  const orderData = {\n    amount: 1000.00,\n    orderid: 'ORDER' + Date.now(),\n    payee_fname: 'John',\n    payee_lname: 'Doe',\n    payee_mobile: '9876543210',\n    payee_email: 'customer@example.com',\n    callbackurl: 'https://yoursite.com/callback'\n  };\n\n  const encryptedData = encryptAES(orderData);\n\n  try {\n    const response = await axios.post(\n      'https://api.rupipay.shop/api/v1/payin/order/create',\n      { data: encryptedData },\n      {\n        headers: {\n          'X-Authorization-Key': AUTH_KEY,\n          'X-Module-Secret': MODULE_SECRET,\n          'Content-Type': 'application/json'\n        }\n      }\n    );\n\n    console.log('Order created:', response.data);\n  } catch (error) {\n    console.error('Error:', error.response?.data || error.message);\n  }\n}\n\ncreatePayinOrder();`, 'payin-nodejs')}
                        className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                      >
                        {copiedCode === 'payin-nodejs' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-400" />
                        ) : (
                          <Copy className="h-4 w-4 text-gray-400" />
                        )}
                      </button>
                    </div>
                  </TabsContent>

                  <TabsContent value="python" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`import requests
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import time

AUTH_KEY = 'your_authorization_key'
MODULE_SECRET = 'your_module_secret'
AES_KEY = bytes.fromhex('your_aes_key')
AES_IV = bytes.fromhex('your_aes_iv')

def encrypt_aes(data):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    json_data = json.dumps(data)
    padded_data = pad(json_data.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')

def create_payin_order():
    order_data = {
        'amount': 1000.00,
        'orderid': f'ORDER{int(time.time() * 1000)}',
        'payee_fname': 'John',
        'payee_lname': 'Doe',
        'payee_mobile': '9876543210',
        'payee_email': 'customer@example.com',
        'callbackurl': 'https://yoursite.com/callback'
    }
    
    encrypted_data = encrypt_aes(order_data)
    
    headers = {
        'X-Authorization-Key': AUTH_KEY,
        'X-Module-Secret': MODULE_SECRET,
        'Content-Type': 'application/json'
    }
    
    payload = {'data': encrypted_data}
    
    try:
        response = requests.post(
            'https://api.rupipay.shop/api/payin/order/create',
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            print('Order created:', response.json())
        else:
            print('Error:', response.text)
    except Exception as e:
        print('Exception:', str(e))

if __name__ == '__main__':
    create_payin_order()`}
                      </pre>
                      <button
                        onClick={() => copyToClipboard(`import requests\nimport json\nimport base64\nfrom Crypto.Cipher import AES\nfrom Crypto.Util.Padding import pad\nimport time\n\nAUTH_KEY = 'your_authorization_key'\nMODULE_SECRET = 'your_module_secret'\nAES_KEY = bytes.fromhex('your_aes_key')\nAES_IV = bytes.fromhex('your_aes_iv')\n\ndef encrypt_aes(data):\n    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)\n    json_data = json.dumps(data)\n    padded_data = pad(json_data.encode('utf-8'), AES.block_size)\n    encrypted = cipher.encrypt(padded_data)\n    return base64.b64encode(encrypted).decode('utf-8')\n\ndef create_payin_order():\n    order_data = {\n        'amount': 1000.00,\n        'orderid': f'ORDER{int(time.time() * 1000)}',\n        'payee_fname': 'John',\n        'payee_lname': 'Doe',\n        'payee_mobile': '9876543210',\n        'payee_email': 'customer@example.com',\n        'callbackurl': 'https://yoursite.com/callback'\n    }\n    \n    encrypted_data = encrypt_aes(order_data)\n    \n    headers = {\n        'X-Authorization-Key': AUTH_KEY,\n        'X-Module-Secret': MODULE_SECRET,\n        'Content-Type': 'application/json'\n    }\n    \n    payload = {'data': encrypted_data}\n    \n    try:\n        response = requests.post(\n            'https://api.rupipay.shop/api/v1/payin/order/create',\n            json=payload,\n            headers=headers\n        )\n        \n        if response.status_code == 200:\n            print('Order created:', response.json())\n    except Exception as e:\n        print('Exception:', str(e))\n\nif __name__ == '__main__':\n    create_payin_order()`, 'payin-python')}
                        className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                      >
                        {copiedCode === 'payin-python' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-400" />
                        ) : (
                          <Copy className="h-4 w-4 text-gray-400" />
                        )}
                      </button>
                    </div>
                  </TabsContent>

                  <TabsContent value="java" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.net.http.*;
import java.net.URI;
import java.util.*;
import com.google.gson.Gson;

public class PaysetuPayIN {
    private static final String AUTH_KEY = "your_authorization_key";
    private static final String MODULE_SECRET = "your_module_secret";
    private static final String AES_KEY = "your_aes_key";
    private static final String AES_IV = "your_aes_iv";
    
    public static String encryptAES(String data) throws Exception {
        byte[] keyBytes = hexStringToByteArray(AES_KEY);
        byte[] ivBytes = hexStringToByteArray(AES_IV);
        
        SecretKeySpec secretKey = new SecretKeySpec(keyBytes, "AES");
        IvParameterSpec iv = new IvParameterSpec(ivBytes);
        
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, iv);
        
        byte[] encrypted = cipher.doFinal(data.getBytes("UTF-8"));
        return Base64.getEncoder().encodeToString(encrypted);
    }
    
    private static byte[] hexStringToByteArray(String s) {
        int len = s.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(s.charAt(i), 16) << 4)
                                 + Character.digit(s.charAt(i+1), 16));
        }
        return data;
    }
    
    public static void createPayinOrder() throws Exception {
        Gson gson = new Gson();
        
        Map<String, Object> orderData = new HashMap<>();
        orderData.put("amount", 1000.00);
        orderData.put("orderid", "ORDER" + System.currentTimeMillis());
        orderData.put("payee_fname", "John");
        orderData.put("payee_lname", "Doe");
        orderData.put("payee_mobile", "9876543210");
        orderData.put("payee_email", "customer@example.com");
        
        String jsonData = gson.toJson(orderData);
        String encryptedData = encryptAES(jsonData);
        
        Map<String, String> payload = new HashMap<>();
        payload.put("data", encryptedData);
        
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("https://api.rupipay.shop/api/payin/order/create"))
            .header("X-Authorization-Key", AUTH_KEY)
            .header("X-Module-Secret", MODULE_SECRET)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(payload)))
            .build();
        
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
        
        System.out.println("Response: " + response.body());
    }
    
    public static void main(String[] args) {
        try {
            createPayinOrder();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}`}
                      </pre>
                      <button
                        onClick={() => copyToClipboard(`import javax.crypto.Cipher;\nimport javax.crypto.spec.IvParameterSpec;\nimport javax.crypto.spec.SecretKeySpec;\nimport java.net.http.*;\nimport java.net.URI;\nimport java.util.*;\nimport com.google.gson.Gson;\n\npublic class PaysetuPayIN {\n    private static final String AUTH_KEY = "your_authorization_key";\n    private static final String MODULE_SECRET = "your_module_secret";\n    private static final String AES_KEY = "your_aes_key";\n    private static final String AES_IV = "your_aes_iv";\n    \n    public static String encryptAES(String data) throws Exception {\n        byte[] keyBytes = hexStringToByteArray(AES_KEY);\n        byte[] ivBytes = hexStringToByteArray(AES_IV);\n        \n        SecretKeySpec secretKey = new SecretKeySpec(keyBytes, "AES");\n        IvParameterSpec iv = new IvParameterSpec(ivBytes);\n        \n        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");\n        cipher.init(Cipher.ENCRYPT_MODE, secretKey, iv);\n        \n        byte[] encrypted = cipher.doFinal(data.getBytes("UTF-8"));\n        return Base64.getEncoder().encodeToString(encrypted);\n    }\n    \n    public static void createPayinOrder() throws Exception {\n        Gson gson = new Gson();\n        \n        Map<String, Object> orderData = new HashMap<>();\n        orderData.put("amount", 1000.00);\n        orderData.put("orderid", "ORDER" + System.currentTimeMillis());\n        orderData.put("payee_fname", "John");\n        orderData.put("payee_lname", "Doe");\n        orderData.put("payee_mobile", "9876543210");\n        orderData.put("payee_email", "customer@example.com");\n        \n        String jsonData = gson.toJson(orderData);\n        String encryptedData = encryptAES(jsonData);\n        \n        Map<String, String> payload = new HashMap<>();\n        payload.put("data", encryptedData);\n        \n        HttpClient client = HttpClient.newHttpClient();\n        HttpRequest request = HttpRequest.newBuilder()\n            .uri(URI.create("https://api.rupipay.shop/api/v1/payin/order/create"))\n            .header("X-Authorization-Key", AUTH_KEY)\n            .header("X-Module-Secret", MODULE_SECRET)\n            .header("Content-Type", "application/json")\n            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(payload)))\n            .build();\n        \n        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\n        System.out.println("Response: " + response.body());\n    }\n    \n    public static void main(String[] args) {\n        try {\n            createPayinOrder();\n        } catch (Exception e) {\n            e.printStackTrace();\n        }\n    }\n}`, 'payin-java')}
                        className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                      >
                        {copiedCode === 'payin-java' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-400" />
                        ) : (
                          <Copy className="h-4 w-4 text-gray-400" />
                        )}
                      </button>
                    </div>
                  </TabsContent>

                  <TabsContent value="dotnet" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`using System;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class PaysetuPayIN
{
    private const string AUTH_KEY = "your_authorization_key";
    private const string MODULE_SECRET = "your_module_secret";
    private const string AES_KEY = "your_aes_key";
    private const string AES_IV = "your_aes_iv";
    
    public static string EncryptAES(string plainText)
    {
        byte[] keyBytes = Convert.FromHexString(AES_KEY);
        byte[] ivBytes = Convert.FromHexString(AES_IV);
        
        using (Aes aes = Aes.Create())
        {
            aes.Key = keyBytes;
            aes.IV = ivBytes;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;
            
            ICryptoTransform encryptor = aes.CreateEncryptor();
            byte[] plainBytes = Encoding.UTF8.GetBytes(plainText);
            byte[] encryptedBytes = encryptor.TransformFinalBlock(
                plainBytes, 0, plainBytes.Length);
            
            return Convert.ToBase64String(encryptedBytes);
        }
    }
    
    public static async Task CreatePayinOrder()
    {
        var orderData = new
        {
            amount = 1000.00,
            orderid = "ORDER" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            payee_fname = "John",
            payee_lname = "Doe",
            payee_mobile = "9876543210",
            payee_email = "customer@example.com",
            callbackurl = "https://yoursite.com/callback"
        };
        
        string jsonData = JsonSerializer.Serialize(orderData);
        string encryptedData = EncryptAES(jsonData);
        
        var payload = new { data = encryptedData };
        string payloadJson = JsonSerializer.Serialize(payload);
        
        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add("X-Authorization-Key", AUTH_KEY);
            client.DefaultRequestHeaders.Add("X-Module-Secret", MODULE_SECRET);
            
            var content = new StringContent(payloadJson, 
                Encoding.UTF8, "application/json");
            
            HttpResponseMessage response = await client.PostAsync(
                "https://api.rupipay.shop/api/payin/order/create",
                content
            );
            
            string responseBody = await response.Content.ReadAsStringAsync();
            Console.WriteLine("Response: " + responseBody);
        }
    }
    
    public static async Task Main(string[] args)
    {
        try
        {
            await CreatePayinOrder();
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
        }
    }
}`}
                      </pre>
                      <button
                        onClick={() => copyToClipboard(`using System;\nusing System.Net.Http;\nusing System.Security.Cryptography;\nusing System.Text;\nusing System.Text.Json;\nusing System.Threading.Tasks;\n\npublic class PaysetuPayIN\n{\n    private const string AUTH_KEY = "your_authorization_key";\n    private const string MODULE_SECRET = "your_module_secret";\n    private const string AES_KEY = "your_aes_key";\n    private const string AES_IV = "your_aes_iv";\n    \n    public static string EncryptAES(string plainText)\n    {\n        byte[] keyBytes = Convert.FromHexString(AES_KEY);\n        byte[] ivBytes = Convert.FromHexString(AES_IV);\n        \n        using (Aes aes = Aes.Create())\n        {\n            aes.Key = keyBytes;\n            aes.IV = ivBytes;\n            aes.Mode = CipherMode.CBC;\n            aes.Padding = PaddingMode.PKCS7;\n            \n            ICryptoTransform encryptor = aes.CreateEncryptor();\n            byte[] plainBytes = Encoding.UTF8.GetBytes(plainText);\n            byte[] encryptedBytes = encryptor.TransformFinalBlock(plainBytes, 0, plainBytes.Length);\n            \n            return Convert.ToBase64String(encryptedBytes);\n        }\n    }\n    \n    public static async Task CreatePayinOrder()\n    {\n        var orderData = new\n        {\n            amount = 1000.00,\n            orderid = "ORDER" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),\n            payee_fname = "John",\n            payee_lname = "Doe",\n            payee_mobile = "9876543210",\n            payee_email = "customer@example.com",\n            callbackurl = "https://yoursite.com/callback"\n        };\n        \n        string jsonData = JsonSerializer.Serialize(orderData);\n        string encryptedData = EncryptAES(jsonData);\n        \n        var payload = new { data = encryptedData };\n        string payloadJson = JsonSerializer.Serialize(payload);\n        \n        using (HttpClient client = new HttpClient())\n        {\n            client.DefaultRequestHeaders.Add("X-Authorization-Key", AUTH_KEY);\n            client.DefaultRequestHeaders.Add("X-Module-Secret", MODULE_SECRET);\n            \n            var content = new StringContent(payloadJson, Encoding.UTF8, "application/json");\n            \n            HttpResponseMessage response = await client.PostAsync(\n                "https://api.rupipay.shop/api/v1/payin/order/create",\n                content\n            );\n            \n            string responseBody = await response.Content.ReadAsStringAsync();\n            Console.WriteLine("Response: " + responseBody);\n        }\n    }\n    \n    public static async Task Main(string[] args)\n    {\n        try\n        {\n            await CreatePayinOrder();\n        }\n        catch (Exception ex)\n        {\n            Console.WriteLine("Error: " + ex.Message);\n        }\n    }\n}`, 'payin-dotnet')}
                        className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                      >
                        {copiedCode === 'payin-dotnet' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-400" />
                        ) : (
                          <Copy className="h-4 w-4 text-gray-400" />
                        )}
                      </button>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payout" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5 text-blue-600" />
                PayOUT API - Disburse Funds
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-gray-600 mb-4">
                  The PayOUT API allows you to transfer funds to any bank account via IMPS, NEFT, or RTGS. 
                  No need to pre-register bank accounts - provide bank details directly in the request.
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-2">How Payout Charges Work</h4>
                      <p className="text-sm text-blue-800 mb-2">
                        Charges are calculated in reverse - the beneficiary receives the FULL requested amount, 
                        and charges are added to your wallet deduction.
                      </p>
                      <div className="bg-blue-100 p-3 rounded mt-2">
                        <p className="text-sm text-blue-900 font-semibold mb-1">Example:</p>
                        <p className="text-sm text-blue-800">• Requested Amount: ₹100</p>
                        <p className="text-sm text-blue-800">• Payout Charge: ₹10</p>
                        <p className="text-sm text-blue-800">• Wallet Deduction: ₹110 (100 + 10)</p>
                        <p className="text-sm text-blue-800">• Bank Credit: ₹100 (Full amount)</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-yellow-900 mb-1">Important</h4>
                      <p className="text-sm text-yellow-800">
                        Ensure you have sufficient wallet balance (amount + charges) before initiating payouts.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Direct Payout (Recommended)</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST /api/payout/client/direct-payout</code>
                  </p>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Headers</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`Authorization: Bearer your_jwt_token
X-Authorization-Key: your_authorization_key
X-Module-Secret: your_module_secret
Content-Type: application/json`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Body</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "order_id": "MERCHANT_ORDER_12345",
  "amount": 1000.00,
  "tpin": "1234",
  "account_holder_name": "John Doe",
  "account_number": "1234567890",
  "ifsc_code": "SBIN0001234",
  "bank_name": "State Bank of India",
  "payment_type": "IMPS",
  "purpose": "Vendor Payment",
  "bene_email": "john@example.com",
  "bene_mobile": "9876543210"
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`{\n  "order_id": "MERCHANT_ORDER_12345",\n  "amount": 1000.00,\n  "tpin": "1234",\n  "account_holder_name": "John Doe",\n  "account_number": "1234567890",\n  "ifsc_code": "SBIN0001234",\n  "bank_name": "State Bank of India",\n  "payment_type": "IMPS",\n  "purpose": "Vendor Payment",\n  "bene_email": "john@example.com",\n  "bene_mobile": "9876543210"\n}`, 'payout-req')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'payout-req' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Parameters</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="border p-2 text-left">Parameter</th>
                        <th className="border p-2 text-left">Type</th>
                        <th className="border p-2 text-left">Required</th>
                        <th className="border p-2 text-left">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border p-2 font-mono">order_id</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Unique order identifier from your system (prevents duplicate payouts)</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">amount</td>
                        <td className="border p-2">Number</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Payout amount in INR</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">tpin</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">4-digit Transaction PIN</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">account_holder_name</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Beneficiary account holder name</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">account_number</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Beneficiary bank account number</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">ifsc_code</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Bank IFSC code (11 characters)</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">bank_name</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">Yes</td>
                        <td className="border p-2">Bank name</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">payment_type</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">IMPS, NEFT, or RTGS (default: IMPS)</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">purpose</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">Payment purpose (default: "Payout")</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">bene_email</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">Beneficiary email address</td>
                      </tr>
                      <tr>
                        <td className="border p-2 font-mono">bene_mobile</td>
                        <td className="border p-2">String</td>
                        <td className="border p-2">No</td>
                        <td className="border p-2">Beneficiary mobile number</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Success Response</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "message": "Payout initiated successfully",
  "txn_id": "TXN1A2B3C4D5E6F7",
  "reference_id": "DP20250225120000ABC123",
  "order_id": "MERCHANT_ORDER_12345",
  "amount": 1000.00,
  "charges": 10.00,
  "net_amount": 990.00,
  "status": "QUEUED",
  "beneficiary": {
    "name": "John Doe",
    "account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
    "bank_name": "State Bank of India"
  }
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`{\n  "success": true,\n  "message": "Payout initiated successfully",\n  "txn_id": "TXN1A2B3C4D5E6F7",\n  "reference_id": "DP20250225120000ABC123",\n  "order_id": "MERCHANT_ORDER_12345",\n  "amount": 1000.00,\n  "charges": 10.00,\n  "net_amount": 990.00,\n  "status": "QUEUED",\n  "beneficiary": {\n    "name": "John Doe",\n    "account_number": "1234567890",\n    "ifsc_code": "SBIN0001234",\n    "bank_name": "State Bank of India"\n  }\n}`, 'payout-res')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'payout-res' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Error Response</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": false,
  "message": "Invalid TPIN"
}

// OR

{
  "success": false,
  "message": "Insufficient balance. Required: ₹1000, Available: ₹500"
}

// OR (Duplicate Order ID)

{
  "success": false,
  "message": "Payout failed: Duplicate order_id. A payout with order_id MERCHANT_ORDER_12345 already exists",
  "existing_txn_id": "TXN1A2B3C4D5E6F7",
  "existing_status": "SUCCESS"
}`}
                  </pre>
                </div>

                <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mt-4">
                  <h4 className="font-semibold text-yellow-900 mb-2">⚠️ Important: Order ID Requirements</h4>
                  <ul className="text-sm text-yellow-800 space-y-1">
                    <li>• <strong>order_id</strong> is now a required field for all payout requests</li>
                    <li>• Must be unique per merchant (prevents duplicate payouts)</li>
                    <li>• Can be any alphanumeric string from your system (e.g., "INV-2024-001", "ORDER_12345")</li>
                    <li>• Duplicate order_id will result in payout rejection with error message</li>
                    <li>• Use this to track payouts in your system and prevent accidental duplicates</li>
                    <li>• Different merchants can use the same order_id (uniqueness is per merchant)</li>
                  </ul>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Payment Types</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="border rounded-lg p-4 bg-gradient-to-br from-blue-50 to-white">
                    <h4 className="font-semibold text-blue-900 mb-2">IMPS</h4>
                    <ul className="text-sm text-gray-700 space-y-1">
                      <li>• Instant transfer (within seconds)</li>
                      <li>• Available 24x7</li>
                      <li>• Up to ₹5,00,000 per transaction</li>
                      <li>• Best for urgent payments</li>
                    </ul>
                  </div>
                  <div className="border rounded-lg p-4 bg-gradient-to-br from-green-50 to-white">
                    <h4 className="font-semibold text-green-900 mb-2">NEFT</h4>
                    <ul className="text-sm text-gray-700 space-y-1">
                      <li>• Within 2 hours</li>
                      <li>• Available 24x7</li>
                      <li>• No maximum limit</li>
                      <li>• Best for regular payments</li>
                    </ul>
                  </div>
                  <div className="border rounded-lg p-4 bg-gradient-to-br from-purple-50 to-white">
                    <h4 className="font-semibold text-purple-900 mb-2">RTGS</h4>
                    <ul className="text-sm text-gray-700 space-y-1">
                      <li>• Real-time (within 30 min)</li>
                      <li>• 7 AM - 6 PM (working days)</li>
                      <li>• Minimum ₹2,00,000</li>
                      <li>• Best for large amounts</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Payout Status Values</h3>
                <div className="space-y-2">
                  <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                    <span className="font-mono font-semibold text-blue-700">INITIATED</span>
                    <p className="text-sm text-blue-800">Payout request created, pending processing</p>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg">
                    <span className="font-mono font-semibold text-yellow-700">QUEUED</span>
                    <p className="text-sm text-yellow-800">Payout queued with payment gateway</p>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                    <span className="font-mono font-semibold text-orange-700">INPROCESS</span>
                    <p className="text-sm text-orange-800">Payout being processed by bank</p>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                    <span className="font-mono font-semibold text-green-700">SUCCESS</span>
                    <p className="text-sm text-green-800">Payout completed successfully</p>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                    <span className="font-mono font-semibold text-red-700">FAILED</span>
                    <p className="text-sm text-red-800">Payout failed, amount refunded to wallet</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Check Payout Status (Instant)</h3>
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Endpoint:</strong> <code className="bg-blue-100 px-2 py-1 rounded">POST https://api.rupipay.shop/api/payout/client/check-status/{'<TXN_ID>'}</code>
                  </p>
                </div>

                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-green-900 mb-2">Recommended Workflow</h4>
                      <ol className="text-sm text-green-800 space-y-1 list-decimal list-inside">
                        <li>Initiate payout using Direct Payout API</li>
                        <li>Immediately call this check-status API with the returned txn_id</li>
                        <li>Get instant SUCCESS status confirmation</li>
                        <li>No need to wait for webhooks or poll repeatedly</li>
                      </ol>
                    </div>
                  </div>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request Headers</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`Authorization: Bearer your_jwt_token
X-Authorization-Key: your_authorization_key
X-Module-Secret: your_module_secret
Content-Type: application/json`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Request (No Body Required)</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`POST https://api.rupipay.shop/api/payout/client/check-status/TXN1A2B3C4D5E6F7`}
                  </pre>
                </div>

                <h4 className="font-semibold mb-2 mt-4">Success Response</h4>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "success": true,
  "message": "Payout status retrieved successfully",
  "data": {
    "txn_id": "TXN1A2B3C4D5E6F7",
    "reference_id": "DP20250225120000ABC123",
    "order_id": "MERCHANT_ORDER_12345",
    "amount": 1000.00,
    "charges": 10.00,
    "status": "SUCCESS",
    "utr": "UTR123456789012",
    "beneficiary": {
      "name": "John Doe",
      "account_number": "1234567890",
      "ifsc_code": "SBIN0001234",
      "bank_name": "State Bank of India"
    },
    "created_at": "2026-02-25T12:00:00Z",
    "updated_at": "2026-02-25T12:00:30Z"
  }
}`}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(`{\n  "success": true,\n  "message": "Payout status retrieved successfully",\n  "data": {\n    "txn_id": "TXN1A2B3C4D5E6F7",\n    "reference_id": "DP20250225120000ABC123",\n    "order_id": "MERCHANT_ORDER_12345",\n    "amount": 1000.00,\n    "charges": 10.00,\n    "status": "SUCCESS",\n    "utr": "UTR123456789012",\n    "beneficiary": {\n      "name": "John Doe",\n      "account_number": "1234567890",\n      "ifsc_code": "SBIN0001234",\n      "bank_name": "State Bank of India"\n    },\n    "created_at": "2026-02-25T12:00:00Z",\n    "updated_at": "2026-02-25T12:00:30Z"\n  }\n}`, 'check-status-res')}
                    className="absolute top-2 right-2 p-2 hover:bg-gray-800 rounded"
                  >
                    {copiedCode === 'check-status-res' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-400" />
                    ) : (
                      <Copy className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">Complete Integration Example with Status Check</h3>
                <Tabs defaultValue="nodejs" className="w-full">
                  <TabsList className="grid w-full max-w-2xl grid-cols-5">
                    <TabsTrigger value="nodejs">Node.js</TabsTrigger>
                    <TabsTrigger value="python">Python</TabsTrigger>
                    <TabsTrigger value="java">Java</TabsTrigger>
                    <TabsTrigger value="php">PHP</TabsTrigger>
                    <TabsTrigger value="dotnet">.NET</TabsTrigger>
                  </TabsList>

                  <TabsContent value="nodejs" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`const axios = require('axios');

const API_BASE = 'https://api.rupipay.shop/api';
const AUTH_KEY = 'your_authorization_key';
const MODULE_SECRET = 'your_module_secret';

// Step 1: Login to get Bearer token
async function getToken() {
  const response = await axios.post(\`\${API_BASE}/merchant/login\`, {
    merchantId: 'your_merchant_id',
    password: 'your_password'
  });
  return response.data.token;
}

// Step 2: Initiate payout
async function sendPayout(token) {
  try {
    const response = await axios.post(
      \`\${API_BASE}/payout/client/direct-payout\`,
      {
        order_id: 'ORDER_' + Date.now(),
        amount: 100.00,
        tpin: '1234',
        account_holder_name: 'John Doe',
        account_number: '1234567890',
        ifsc_code: 'SBIN0001234',
        bank_name: 'State Bank of India',
        payment_type: 'IMPS',
        purpose: 'Vendor Payment'
      },
      {
        headers: {
          'Authorization': \`Bearer \${token}\`,
          'X-Authorization-Key': AUTH_KEY,
          'X-Module-Secret': MODULE_SECRET,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('✓ Payout initiated');
    console.log('TXN ID:', response.data.txn_id);
    return response.data.txn_id;
  } catch (error) {
    console.error('✗ Payout failed:', error.response?.data);
    throw error;
  }
}

// Step 3: Check payout status instantly
async function checkPayoutStatus(token, txnId) {
  try {
    const response = await axios.post(
      \`\${API_BASE}/payout/client/check-status/\${txnId}\`,
      {},
      {
        headers: {
          'Authorization': \`Bearer \${token}\`,
          'X-Authorization-Key': AUTH_KEY,
          'X-Module-Secret': MODULE_SECRET,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('✓ Status:', response.data.data.status);
    console.log('UTR:', response.data.data.utr);
    return response.data.data;
  } catch (error) {
    console.error('✗ Status check failed:', error.response?.data);
    throw error;
  }
}

// Execute
async function main() {
  const token = await getToken();
  const txnId = await sendPayout(token);
  await checkPayoutStatus(token, txnId);
}

main();`}
                      </pre>
                    </div>
                  </TabsContent>

                  <TabsContent value="python" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`import requests
import time

API_BASE = 'https://api.rupipay.shop/api'
AUTH_KEY = 'your_authorization_key'
MODULE_SECRET = 'your_module_secret'

# Step 1: Login to get Bearer token
def get_token():
    response = requests.post(
        f'{API_BASE}/merchant/login',
        json={
            'merchantId': 'your_merchant_id',
            'password': 'your_password'
        }
    )
    return response.json()['token']

# Step 2: Initiate payout
def send_payout(token):
    response = requests.post(
        f'{API_BASE}/payout/client/direct-payout',
        json={
            'order_id': f'ORDER_{int(time.time() * 1000)}',
            'amount': 100.00,
            'tpin': '1234',
            'account_holder_name': 'John Doe',
            'account_number': '1234567890',
            'ifsc_code': 'SBIN0001234',
            'bank_name': 'State Bank of India',
            'payment_type': 'IMPS',
            'purpose': 'Vendor Payment'
        },
        headers={
            'Authorization': f'Bearer {token}',
            'X-Authorization-Key': AUTH_KEY,
            'X-Module-Secret': MODULE_SECRET,
            'Content-Type': 'application/json'
        }
    )
    data = response.json()
    print(f'✓ Payout initiated: {data["txn_id"]}')
    return data['txn_id']

# Step 3: Check payout status instantly
def check_payout_status(token, txn_id):
    response = requests.post(
        f'{API_BASE}/payout/client/check-status/{txn_id}',
        json={},
        headers={
            'Authorization': f'Bearer {token}',
            'X-Authorization-Key': AUTH_KEY,
            'X-Module-Secret': MODULE_SECRET,
            'Content-Type': 'application/json'
        }
    )
    data = response.json()['data']
    print(f'✓ Status: {data["status"]}, UTR: {data["utr"]}')
    return data

# Execute
if __name__ == '__main__':
    token = get_token()
    txn_id = send_payout(token)
    check_payout_status(token, txn_id)`}
                      </pre>
                    </div>
                  </TabsContent>

                  <TabsContent value="java" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`import java.net.http.*;
import java.net.URI;
import java.util.*;
import com.google.gson.Gson;

public class PayoutAPI {
    static final String API_BASE = "https://api.rupipay.shop/api";
    static final String AUTH_KEY = "your_authorization_key";
    static final String MODULE_SECRET = "your_module_secret";
    static final Gson gson = new Gson();
    static final HttpClient client = HttpClient.newHttpClient();
    
    // Step 1: Login
    public static String getToken() throws Exception {
        Map<String, String> data = Map.of(
            "merchantId", "your_merchant_id",
            "password", "your_password"
        );
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_BASE + "/merchant/login"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(data)))
            .build();
        
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
        Map result = gson.fromJson(response.body(), Map.class);
        return (String) result.get("token");
    }
    
    // Step 2: Initiate payout
    public static String sendPayout(String token) throws Exception {
        Map<String, Object> data = new HashMap<>();
        data.put("order_id", "ORDER_" + System.currentTimeMillis());
        data.put("amount", 100.00);
        data.put("tpin", "1234");
        data.put("account_holder_name", "John Doe");
        data.put("account_number", "1234567890");
        data.put("ifsc_code", "SBIN0001234");
        data.put("bank_name", "State Bank of India");
        data.put("payment_type", "IMPS");
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_BASE + "/payout/client/direct-payout"))
            .header("Authorization", "Bearer " + token)
            .header("X-Authorization-Key", AUTH_KEY)
            .header("X-Module-Secret", MODULE_SECRET)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(data)))
            .build();
        
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
        Map result = gson.fromJson(response.body(), Map.class);
        System.out.println("✓ Payout: " + result.get("txn_id"));
        return (String) result.get("txn_id");
    }
    
    // Step 3: Check status
    public static void checkStatus(String token, String txnId) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_BASE + "/payout/client/check-status/" + txnId))
            .header("Authorization", "Bearer " + token)
            .header("X-Authorization-Key", AUTH_KEY)
            .header("X-Module-Secret", MODULE_SECRET)
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString("{}"))
            .build();
        
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
        Map result = gson.fromJson(response.body(), Map.class);
        Map data = (Map) result.get("data");
        System.out.println("✓ Status: " + data.get("status"));
    }
    
    public static void main(String[] args) throws Exception {
        String token = getToken();
        String txnId = sendPayout(token);
        checkStatus(token, txnId);
    }
}`}
                      </pre>
                    </div>
                  </TabsContent>

                  <TabsContent value="php" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`<?php

define('API_BASE', 'https://api.rupipay.shop/api');
define('AUTH_KEY', 'your_authorization_key');
define('MODULE_SECRET', 'your_module_secret');

// Step 1: Login
function getToken() {
    $ch = curl_init(API_BASE . '/merchant/login');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
        'merchantId' => 'your_merchant_id',
        'password' => 'your_password'
    ]));
    
    $response = curl_exec($ch);
    curl_close($ch);
    return json_decode($response, true)['token'];
}

// Step 2: Initiate payout
function sendPayout($token) {
    $data = [
        'order_id' => 'ORDER_' . round(microtime(true) * 1000),
        'amount' => 100.00,
        'tpin' => '1234',
        'account_holder_name' => 'John Doe',
        'account_number' => '1234567890',
        'ifsc_code' => 'SBIN0001234',
        'bank_name' => 'State Bank of India',
        'payment_type' => 'IMPS',
        'purpose' => 'Vendor Payment'
    ];
    
    $ch = curl_init(API_BASE . '/payout/client/direct-payout');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . $token,
        'X-Authorization-Key: ' . AUTH_KEY,
        'X-Module-Secret: ' . MODULE_SECRET,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    
    $response = curl_exec($ch);
    curl_close($ch);
    $result = json_decode($response, true);
    echo "✓ Payout: " . $result['txn_id'] . "\\n";
    return $result['txn_id'];
}

// Step 3: Check status
function checkStatus($token, $txnId) {
    $ch = curl_init(API_BASE . '/payout/client/check-status/' . $txnId);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . $token,
        'X-Authorization-Key: ' . AUTH_KEY,
        'X-Module-Secret: ' . MODULE_SECRET,
        'Content-Type: application/json'
    ]);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([]));
    
    $response = curl_exec($ch);
    curl_close($ch);
    $result = json_decode($response, true);
    echo "✓ Status: " . $result['data']['status'] . "\\n";
}

// Execute
$token = getToken();
$txnId = sendPayout($token);
checkStatus($token, $txnId);

?>`}
                      </pre>
                    </div>
                  </TabsContent>

                  <TabsContent value="dotnet" className="mt-4">
                    <div className="relative">
                      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm max-h-96">
{`using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class PayoutAPI
{
    const string API_BASE = "https://api.rupipay.shop/api";
    const string AUTH_KEY = "your_authorization_key";
    const string MODULE_SECRET = "your_module_secret";
    static readonly HttpClient client = new HttpClient();
    
    // Step 1: Login
    public static async Task<string> GetToken()
    {
        var data = new { merchantId = "your_merchant_id", password = "your_password" };
        var content = new StringContent(JsonSerializer.Serialize(data), Encoding.UTF8, "application/json");
        var response = await client.PostAsync($"{API_BASE}/merchant/login", content);
        var result = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(result).GetProperty("token").GetString();
    }
    
    // Step 2: Initiate payout
    public static async Task<string> SendPayout(string token)
    {
        var data = new
        {
            order_id = "ORDER_" + DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            amount = 100.00,
            tpin = "1234",
            account_holder_name = "John Doe",
            account_number = "1234567890",
            ifsc_code = "SBIN0001234",
            bank_name = "State Bank of India",
            payment_type = "IMPS"
        };
        
        var content = new StringContent(JsonSerializer.Serialize(data), Encoding.UTF8, "application/json");
        client.DefaultRequestHeaders.Clear();
        client.DefaultRequestHeaders.Add("Authorization", $"Bearer {token}");
        client.DefaultRequestHeaders.Add("X-Authorization-Key", AUTH_KEY);
        client.DefaultRequestHeaders.Add("X-Module-Secret", MODULE_SECRET);
        
        var response = await client.PostAsync($"{API_BASE}/payout/client/direct-payout", content);
        var result = await response.Content.ReadAsStringAsync();
        var json = JsonSerializer.Deserialize<JsonElement>(result);
        var txnId = json.GetProperty("txn_id").GetString();
        Console.WriteLine($"✓ Payout: {txnId}");
        return txnId;
    }
    
    // Step 3: Check status
    public static async Task CheckStatus(string token, string txnId)
    {
        var content = new StringContent("{}", Encoding.UTF8, "application/json");
        client.DefaultRequestHeaders.Clear();
        client.DefaultRequestHeaders.Add("Authorization", $"Bearer {token}");
        client.DefaultRequestHeaders.Add("X-Authorization-Key", AUTH_KEY);
        client.DefaultRequestHeaders.Add("X-Module-Secret", MODULE_SECRET);
        
        var response = await client.PostAsync($"{API_BASE}/payout/client/check-status/{txnId}", content);
        var result = await response.Content.ReadAsStringAsync();
        var json = JsonSerializer.Deserialize<JsonElement>(result);
        var status = json.GetProperty("data").GetProperty("status").GetString();
        Console.WriteLine($"✓ Status: {status}");
    }
    
    public static async Task Main()
    {
        var token = await GetToken();
        var txnId = await SendPayout(token);
        await CheckStatus(token, txnId);
    }
}`}
                      </pre>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-900 mb-2">Key Features</h4>
                <ul className="text-sm text-green-800 space-y-1 list-disc list-inside">
                  <li>No need to pre-register bank accounts</li>
                  <li>Send payouts to any bank account instantly</li>
                  <li>Beneficiary receives FULL requested amount</li>
                  <li>Charges added to wallet deduction (reverse calculation)</li>
                  <li>Instant status check with check-status API</li>
                  <li>TPIN verification for security</li>
                  <li>Support for IMPS, NEFT, and RTGS</li>
                </ul>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-1">Important Notes</h4>
                    <ul className="text-sm text-blue-800 space-y-2">
                      <li>• All payout requests require Bearer token + API credentials in headers</li>
                      <li>• Use check-status API immediately after payout for instant confirmation</li>
                      <li>• Beneficiary always receives the full requested amount</li>
                      <li>• Charges are added to your wallet deduction (not subtracted from payout)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="webhooks" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-purple-600" />
                Webhooks - Real-time Notifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-gray-600 mb-4">
                  Webhooks allow you to receive real-time notifications about transaction status changes. 
                  Configure your callback URL in the API request to receive instant updates.
                </p>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">PayIN Webhook</h3>
                <p className="text-gray-600 mb-3">
                  When a PayIN transaction status changes, we'll send a POST request to your callback URL:
                </p>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "event": "payin.status.update",
  "txn_id": "TXN20260216123456ABC",
  "order_id": "ORDER123456789",
  "amount": 1000.00,
  "status": "SUCCESS",
  "utr": "UTR123456789",
  "timestamp": "2026-02-16T10:31:00Z"
}`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3 text-lg">PayOUT Webhook</h3>
                <p className="text-gray-600 mb-3">
                  When a PayOUT transaction status changes, we'll send a POST request to your callback URL:
                </p>
                <div className="relative">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm">
{`{
  "event": "payout.status.update",
  "txn_id": "PAYOUT20260216123456XYZ",
  "reference_id": "PAYOUT123456789",
  "amount": 5000.00,
  "status": "SUCCESS",
  "utr": "UTR987654321",
  "timestamp": "2026-02-16T10:32:00Z"
}`}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Quick Links</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a href="/developer/credentials" className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <Key className="h-6 w-6 text-purple-600 mb-2" />
              <h3 className="font-semibold mb-1">API Credentials</h3>
              <p className="text-sm text-gray-600">View your API keys and secrets</p>
            </a>
            <a href="https://api.rupipay.shop" target="_blank" rel="noopener noreferrer" className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <Code className="h-6 w-6 text-blue-600 mb-2" />
              <h3 className="font-semibold mb-1">API Base URL</h3>
              <p className="text-sm text-gray-600">https://api.rupipay.shop</p>
            </a>
            <a href="/support" className="p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <Zap className="h-6 w-6 text-orange-600 mb-2" />
              <h3 className="font-semibold mb-1">Support</h3>
              <p className="text-sm text-gray-600">Get help with integration</p>
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}



