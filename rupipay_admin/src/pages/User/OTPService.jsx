import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { MessageSquare, Send } from 'lucide-react'

export default function OTPService() {
  const [config, setConfig] = useState({
    provider: 'SMS Gateway',
    apiKey: '',
    senderId: 'MONONE',
    otpLength: 6,
    expiryMinutes: 5,
  })

  const [testPhone, setTestPhone] = useState('')

  const handleSaveConfig = (e) => {
    e.preventDefault()
    alert('OTP configuration saved successfully!')
  }

  const handleTestOTP = () => {
    if (!testPhone) {
      alert('Please enter a phone number')
      return
    }
    alert(`Test OTP sent to ${testPhone}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <MessageSquare className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold">OTP Service</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>OTP Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveConfig} className="space-y-4">
              <div>
                <Label>Provider</Label>
                <Input
                  value={config.provider}
                  onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                />
              </div>
              <div>
                <Label>API Key</Label>
                <Input
                  type="password"
                  value={config.apiKey}
                  onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                  placeholder="Enter API key"
                />
              </div>
              <div>
                <Label>Sender ID</Label>
                <Input
                  value={config.senderId}
                  onChange={(e) => setConfig({ ...config, senderId: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>OTP Length</Label>
                  <Input
                    type="number"
                    value={config.otpLength}
                    onChange={(e) => setConfig({ ...config, otpLength: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Expiry (Minutes)</Label>
                  <Input
                    type="number"
                    value={config.expiryMinutes}
                    onChange={(e) => setConfig({ ...config, expiryMinutes: e.target.value })}
                  />
                </div>
              </div>
              <Button type="submit" className="w-full">Save Configuration</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Test OTP Service</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Phone Number</Label>
              <Input
                placeholder="+91 9876543210"
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value)}
              />
            </div>
            <Button onClick={handleTestOTP} className="w-full">
              <Send className="h-4 w-4 mr-2" />
              Send Test OTP
            </Button>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-medium mb-2">Recent OTP Logs</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>+91 9876543210</span>
                  <span className="text-green-600">Delivered</span>
                </div>
                <div className="flex justify-between">
                  <span>+91 9876543211</span>
                  <span className="text-green-600">Delivered</span>
                </div>
                <div className="flex justify-between">
                  <span>+91 9876543212</span>
                  <span className="text-red-600">Failed</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
