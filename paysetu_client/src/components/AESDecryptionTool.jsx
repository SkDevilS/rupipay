import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Lock, Unlock, Copy, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'

export default function AESDecryptionTool({ aesKey, aesIv }) {
  const [encryptedText, setEncryptedText] = useState('')
  const [decryptedText, setDecryptedText] = useState('')
  const [loading, setLoading] = useState(false)

  const handleDecrypt = async () => {
    if (!encryptedText.trim()) {
      toast.error('Please enter encrypted text')
      return
    }

    try {
      setLoading(true)
      
      // Import crypto-js for AES decryption
      const CryptoJS = await import('crypto-js')
      
      // Prepare key and IV
      const key = CryptoJS.enc.Utf8.parse(aesKey.padEnd(32, '\0').substring(0, 32))
      const iv = CryptoJS.enc.Utf8.parse(aesIv.padEnd(16, '\0').substring(0, 16))
      
      // Decrypt
      const decrypted = CryptoJS.AES.decrypt(encryptedText, key, {
        iv: iv,
        mode: CryptoJS.mode.CBC,
        padding: CryptoJS.pad.Pkcs7
      })
      
      const decryptedStr = decrypted.toString(CryptoJS.enc.Utf8)
      
      if (!decryptedStr) {
        toast.error('Decryption failed. Please check your encrypted text.')
        return
      }
      
      setDecryptedText(decryptedStr)
      toast.success('Decryption successful!')
    } catch (error) {
      console.error('Decryption error:', error)
      toast.error('Decryption failed. Invalid encrypted text or format.')
    } finally {
      setLoading(false)
    }
  }

  const handleEncrypt = async () => {
    if (!decryptedText.trim()) {
      toast.error('Please enter text to encrypt')
      return
    }

    try {
      setLoading(true)
      
      // Import crypto-js for AES encryption
      const CryptoJS = await import('crypto-js')
      
      // Prepare key and IV
      const key = CryptoJS.enc.Utf8.parse(aesKey.padEnd(32, '\0').substring(0, 32))
      const iv = CryptoJS.enc.Utf8.parse(aesIv.padEnd(16, '\0').substring(0, 16))
      
      // Encrypt
      const encrypted = CryptoJS.AES.encrypt(decryptedText, key, {
        iv: iv,
        mode: CryptoJS.mode.CBC,
        padding: CryptoJS.pad.Pkcs7
      })
      
      setEncryptedText(encrypted.toString())
      toast.success('Encryption successful!')
    } catch (error) {
      console.error('Encryption error:', error)
      toast.error('Encryption failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text)
    toast.success(`${label} copied to clipboard!`)
  }

  const handleClear = () => {
    setEncryptedText('')
    setDecryptedText('')
    toast.info('Fields cleared')
  }

  return (
    <Card className="shadow-lg">
      <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
        <div className="flex items-center gap-2">
          <Lock className="h-5 w-5" />
          <CardTitle>AES Encryption/Decryption Tool</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-6 space-y-6">
        {/* Info Alert */}
        <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">How to use this tool:</p>
            <ul className="list-disc list-inside space-y-1 text-blue-800">
              <li>Enter encrypted text and click "Decrypt" to see the original data</li>
              <li>Enter plain text and click "Encrypt" to generate encrypted data</li>
              <li>This tool uses your AES Key and IV for encryption/decryption</li>
            </ul>
          </div>
        </div>

        {/* Encrypted Text */}
        <div className="space-y-2">
          <Label className="text-base font-semibold">Encrypted Text</Label>
          <div className="relative">
            <textarea
              value={encryptedText}
              onChange={(e) => setEncryptedText(e.target.value)}
              placeholder="Enter encrypted text here..."
              className="w-full min-h-[120px] p-3 border border-gray-300 rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            {encryptedText && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(encryptedText, 'Encrypted text')}
                className="absolute top-2 right-2"
              >
                <Copy className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-center">
          <Button
            onClick={handleDecrypt}
            disabled={loading || !encryptedText.trim()}
            className="bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700"
          >
            <Unlock className="h-4 w-4 mr-2" />
            Decrypt
          </Button>
          <Button
            onClick={handleEncrypt}
            disabled={loading || !decryptedText.trim()}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Lock className="h-4 w-4 mr-2" />
            Encrypt
          </Button>
          <Button
            onClick={handleClear}
            variant="outline"
            disabled={loading}
          >
            Clear
          </Button>
        </div>

        {/* Decrypted Text */}
        <div className="space-y-2">
          <Label className="text-base font-semibold">Decrypted / Plain Text</Label>
          <div className="relative">
            <textarea
              value={decryptedText}
              onChange={(e) => setDecryptedText(e.target.value)}
              placeholder="Decrypted text will appear here..."
              className="w-full min-h-[120px] p-3 border border-gray-300 rounded-lg font-mono text-sm resize-y focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            {decryptedText && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(decryptedText, 'Decrypted text')}
                className="absolute top-2 right-2"
              >
                <Copy className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Credentials Display */}
        <div className="border-t pt-6 mt-6">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Your Encryption Credentials:</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <Label className="text-xs text-gray-600">AES Key</Label>
              <p className="font-mono text-xs text-gray-800 break-all">{aesKey}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <Label className="text-xs text-gray-600">AES IV</Label>
              <p className="font-mono text-xs text-gray-800 break-all">{aesIv}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
