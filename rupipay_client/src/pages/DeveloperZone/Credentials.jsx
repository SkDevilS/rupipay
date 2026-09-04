import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  KeyRound, Shield, Copy, 
  Eye, EyeOff, Lock, Loader2,
  ArrowRightLeft, FileKey, RefreshCw
} from 'lucide-react'
import { toast } from 'sonner'
import clientAPI from '@/api/client_api'
import PinVerificationDialog from '@/components/PinVerificationDialog'

export default function Credentials() {
  const [loading, setLoading] = useState(true)
  const [credentials, setCredentials] = useState(null)
  const [showAuthKey, setShowAuthKey] = useState(false)
  const [showModuleSecret, setShowModuleSecret] = useState(false)
  const [showAesIv, setShowAesIv] = useState(false)
  const [showAesKey, setShowAesKey] = useState(false)
  const [encryptionMode, setEncryptionMode] = useState('encrypt')
  const [plainText, setPlainText] = useState('')
  const [encryptedText, setEncryptedText] = useState('')
  const [decryptedText, setDecryptedText] = useState('')
  const [processing, setProcessing] = useState(false)
  
  // PIN verification states
  const [pinVerified, setPinVerified] = useState(false)
  const [showPinDialog, setShowPinDialog] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [hasPinSet, setHasPinSet] = useState(true)

  useEffect(() => {
    console.log('=== CREDENTIALS PAGE V2.0 ===')
    loadCredentials()
    checkPinStatus()
    
    // Reset PIN verification when component unmounts or page changes
    return () => {
      setPinVerified(false)
      setShowAuthKey(false)
      setShowModuleSecret(false)
      setShowAesIv(false)
      setShowAesKey(false)
    }
  }, [])

  const checkPinStatus = async () => {
    try {
      const response = await clientAPI.checkPinStatus()
      if (response.success) {
        setHasPinSet(response.hasPinSet)
      }
    } catch (error) {
      console.error('Error checking PIN status:', error)
    }
  }

  const loadCredentials = async () => {
    try {
      setLoading(true)
      const response = await clientAPI.getCredentials()
      console.log('API Response:', response)
      if (response.success) {
        setCredentials(response.credentials)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to load credentials')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (text, label) => {
    if (!text) return toast.error('No value to copy')
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied!`)
  }

  const handleEncrypt = async () => {
    if (!plainText.trim()) return toast.error('Enter text to encrypt')
    try {
      setProcessing(true)
      const response = await clientAPI.encryptData(plainText)
      if (response.success) {
        setEncryptedText(response.encryptedText)
        toast.success('Encrypted!')
      }
    } catch (error) {
      toast.error(error.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleDecrypt = async () => {
    if (!encryptedText.trim()) return toast.error('Enter encrypted text')
    try {
      setProcessing(true)
      const response = await clientAPI.decryptData(encryptedText)
      if (response.success) {
        setDecryptedText(response.decryptedText)
        toast.success('Decrypted!')
      }
    } catch (error) {
      toast.error(error.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleToggleVisibility = (credentialType) => {
    // Check if PIN is set first
    if (!hasPinSet) {
      toast.error('Please set your transaction PIN first to view credentials', {
        duration: 4000,
        action: {
          label: 'Set PIN',
          onClick: () => window.location.href = '/security/change-pin'
        }
      })
      return
    }

    if (!pinVerified) {
      setPendingAction(credentialType)
      setShowPinDialog(true)
      return
    }

    // If PIN already verified, toggle visibility
    switch (credentialType) {
      case 'authKey':
        setShowAuthKey(!showAuthKey)
        break
      case 'moduleSecret':
        setShowModuleSecret(!showModuleSecret)
        break
      case 'aesIv':
        setShowAesIv(!showAesIv)
        break
      case 'aesKey':
        setShowAesKey(!showAesKey)
        break
    }
  }

  const handlePinVerified = () => {
    setPinVerified(true)
    
    // Execute pending action if any
    if (pendingAction) {
      switch (pendingAction) {
        case 'authKey':
          setShowAuthKey(true)
          break
        case 'moduleSecret':
          setShowModuleSecret(true)
          break
        case 'aesIv':
          setShowAesIv(true)
          break
        case 'aesKey':
          setShowAesKey(true)
          break
      }
      setPendingAction(null)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
        <p className="text-gray-600 font-medium">Loading credentials...</p>
        <p className="text-xs text-gray-400">Version 2.0</p>
      </div>
    )
  }

  if (!credentials) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <Shield className="h-16 w-16 text-gray-400" />
        <h2 className="text-xl font-semibold">No Credentials Found</h2>
        <Button onClick={loadCredentials} className="bg-purple-600">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <KeyRound className="h-8 w-8 text-purple-600" />
            API Credentials
          </h1>
          <p className="text-xs text-gray-500 mt-1">Version 2.0 - Real-time Data</p>
        </div>
        <Button onClick={loadCredentials} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Shield className="h-6 w-6 text-blue-600 mt-1" />
            <div>
              <h3 className="font-semibold text-lg text-blue-900 mb-2">Your API Credentials</h3>
              <p className="text-sm text-blue-800">
                These credentials are unique to your account. Use them for API integration.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-lg">
        <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              API Credentials
            </CardTitle>
            <span className="text-xs bg-white/20 px-3 py-1 rounded-full">Live Production</span>
          </div>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-lg border-2 border-purple-200">
            <h3 className="font-semibold text-purple-900 mb-3">Quick Access</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white p-3 rounded border">
                <p className="text-xs text-gray-600 mb-1">Merchant ID</p>
                <div className="flex items-center justify-between">
                  <p className="font-mono font-bold text-purple-700">{credentials.merchant_id}</p>
                  <Button variant="ghost" size="sm" onClick={() => handleCopy(credentials.merchant_id, 'Merchant ID')}>
                    <Copy size={14} />
                  </Button>
                </div>
              </div>
              <div className="bg-white p-3 rounded border">
                <p className="text-xs text-gray-600 mb-1">Environment</p>
                <p className="font-mono font-bold text-green-700">{credentials.environment}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="col-span-2 p-4 bg-gray-50 rounded-lg border">
              <Label className="text-sm font-semibold mb-2 block">Authorization Key</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showAuthKey ? 'text' : 'password'}
                    value={credentials.authorization_key || 'N/A'}
                    readOnly
                    className="font-mono text-sm pr-10"
                  />
                  <button
                    onClick={() => handleToggleVisibility('authKey')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-purple-600 transition-colors"
                  >
                    {showAuthKey ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <Button variant="outline" size="icon" onClick={() => handleCopy(credentials.authorization_key, 'Auth Key')}>
                  <Copy size={18} />
                </Button>
              </div>
            </div>

            <div className="col-span-2 p-4 bg-gray-50 rounded-lg border">
              <Label className="text-sm font-semibold mb-2 block">Module Secret</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showModuleSecret ? 'text' : 'password'}
                    value={credentials.module_secret || 'N/A'}
                    readOnly
                    className="font-mono text-sm pr-10"
                  />
                  <button
                    onClick={() => handleToggleVisibility('moduleSecret')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-purple-600 transition-colors"
                  >
                    {showModuleSecret ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <Button variant="outline" size="icon" onClick={() => handleCopy(credentials.module_secret, 'Module Secret')}>
                  <Copy size={18} />
                </Button>
              </div>
            </div>

            <div className="col-span-2 p-4 bg-purple-50 rounded-lg border border-purple-200">
              <Label className="text-sm font-semibold text-purple-900 mb-1 block">Base URL</Label>
              <div className="flex items-center gap-2">
                <p className="font-mono text-sm text-purple-700 flex-1">{credentials.base_url}</p>
                <Button variant="outline" size="sm" onClick={() => handleCopy(credentials.base_url, 'Base URL')}>
                  <Copy size={16} />
                </Button>
              </div>
            </div>

            <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
              <Label className="text-sm font-semibold text-orange-900 mb-2 block">AES IV</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showAesIv ? 'text' : 'password'}
                    value={credentials.aes_iv || 'N/A'}
                    readOnly
                    className="font-mono text-sm pr-10"
                  />
                  <button onClick={() => handleToggleVisibility('aesIv')} className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-orange-600 transition-colors">
                    {showAesIv ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <Button variant="outline" size="icon" onClick={() => handleCopy(credentials.aes_iv, 'AES IV')}>
                  <Copy size={18} />
                </Button>
              </div>
            </div>

            <div className="p-4 bg-pink-50 rounded-lg border border-pink-200">
              <Label className="text-sm font-semibold text-pink-900 mb-2 block">AES Key</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showAesKey ? 'text' : 'password'}
                    value={credentials.aes_key || 'N/A'}
                    readOnly
                    className="font-mono text-sm pr-10"
                  />
                  <button onClick={() => handleToggleVisibility('aesKey')} className="absolute right-3 top-1/2 -translate-y-1/2 hover:text-pink-600 transition-colors">
                    {showAesKey ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <Button variant="outline" size="icon" onClick={() => handleCopy(credentials.aes_key, 'AES Key')}>
                  <Copy size={18} />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-lg">
        <CardHeader className="bg-gradient-to-r from-green-600 to-teal-600 text-white">
          <CardTitle className="flex items-center gap-2">
            <FileKey className="h-5 w-5" />
            AES Encryption Tool
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <Tabs value={encryptionMode} onValueChange={setEncryptionMode}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="encrypt">Encrypt</TabsTrigger>
              <TabsTrigger value="decrypt">Decrypt</TabsTrigger>
            </TabsList>
            <TabsContent value="encrypt" className="space-y-4">
              <div>
                <Label>Plain Text</Label>
                <textarea
                  placeholder="Enter text..."
                  value={plainText}
                  onChange={(e) => setPlainText(e.target.value)}
                  className="w-full min-h-[120px] p-3 border-2 rounded-lg font-mono text-sm"
                />
              </div>
              <div className="flex gap-3">
                <Button onClick={handleEncrypt} disabled={processing} className="bg-green-600">
                  {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Lock className="h-4 w-4 mr-2" />}
                  Encrypt
                </Button>
                <Button onClick={() => { setPlainText(''); setEncryptedText('') }} variant="outline">Clear</Button>
              </div>
              {encryptedText && (
                <div>
                  <Label className="text-green-700">Encrypted Text</Label>
                  <div className="relative">
                    <textarea
                      value={encryptedText}
                      readOnly
                      className="w-full min-h-[120px] p-3 bg-green-50 border-2 border-green-300 rounded-lg font-mono text-sm"
                    />
                    <Button
                      onClick={() => handleCopy(encryptedText, 'Encrypted text')}
                      variant="outline"
                      size="sm"
                      className="absolute top-2 right-2"
                    >
                      <Copy size={16} />
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
            <TabsContent value="decrypt" className="space-y-4">
              <div>
                <Label>Encrypted Text</Label>
                <textarea
                  placeholder="Enter encrypted text..."
                  value={encryptedText}
                  onChange={(e) => setEncryptedText(e.target.value)}
                  className="w-full min-h-[120px] p-3 border-2 rounded-lg font-mono text-sm"
                />
              </div>
              <div className="flex gap-3">
                <Button onClick={handleDecrypt} disabled={processing} className="bg-teal-600">
                  {processing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <ArrowRightLeft className="h-4 w-4 mr-2" />}
                  Decrypt
                </Button>
                <Button onClick={() => { setEncryptedText(''); setDecryptedText('') }} variant="outline">Clear</Button>
              </div>
              {decryptedText && (
                <div>
                  <Label className="text-teal-700">Decrypted Text</Label>
                  <div className="relative">
                    <textarea
                      value={decryptedText}
                      readOnly
                      className="w-full min-h-[120px] p-3 bg-teal-50 border-2 border-teal-300 rounded-lg font-mono text-sm"
                    />
                    <Button
                      onClick={() => handleCopy(decryptedText, 'Decrypted text')}
                      variant="outline"
                      size="sm"
                      className="absolute top-2 right-2"
                    >
                      <Copy size={16} />
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* PIN Verification Dialog */}
      <PinVerificationDialog
        open={showPinDialog}
        onOpenChange={setShowPinDialog}
        onVerified={handlePinVerified}
        title="Verify PIN to View Credentials"
      />
    </div>
  )
}
