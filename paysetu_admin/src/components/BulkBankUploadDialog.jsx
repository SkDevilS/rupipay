import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Download, Upload, Eye, EyeOff, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import adminAPI from '@/api/admin_api'

export default function BulkBankUploadDialog({ open, onOpenChange, onSuccess }) {
  const [step, setStep] = useState(1) // 1: Upload, 2: Preview, 3: TPIN
  const [file, setFile] = useState(null)
  const [previewData, setPreviewData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [tpin, setTpin] = useState('')
  const [showTpin, setShowTpin] = useState(false)

  const handleDownloadTemplate = async () => {
    try {
      await adminAPI.downloadBankTemplate()
      toast.success('Template downloaded successfully!')
    } catch (error) {
      toast.error(error.message || 'Failed to download template')
    }
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        toast.error('Please select a CSV file')
        return
      }
      setFile(selectedFile)
    }
  }

  const handleUploadAndPreview = async () => {
    if (!file) {
      toast.error('Please select a file')
      return
    }

    setLoading(true)
    try {
      const response = await adminAPI.previewBulkBanks(file)
      
      if (response.success) {
        setPreviewData(response)
        
        if (response.validRows === 0) {
          toast.error('No valid banks found in CSV')
        } else {
          toast.success(`Found ${response.validRows} valid bank(s)`)
          setStep(2)
        }
      }
    } catch (error) {
      toast.error(error.message || 'Failed to process CSV')
    } finally {
      setLoading(false)
    }
  }

  const handleProceedToTpin = () => {
    if (!previewData || previewData.validRows === 0) {
      toast.error('No valid banks to add')
      return
    }
    setStep(3)
  }

  const handleSubmit = async () => {
    if (!tpin || tpin.length !== 6) {
      toast.error('Please enter valid 6-digit TPIN')
      return
    }

    setLoading(true)
    try {
      const response = await adminAPI.bulkAddBanks(previewData.banks, tpin)
      
      if (response.success) {
        toast.success(response.message)
        
        if (response.failedCount > 0) {
          toast.warning(`${response.failedCount} bank(s) failed to add`)
        }
        
        // Reset and close
        handleReset()
        onSuccess()
        onOpenChange(false)
      }
    } catch (error) {
      toast.error(error.message || 'Failed to add banks')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setStep(1)
    setFile(null)
    setPreviewData(null)
    setTpin('')
  }

  const handleClose = () => {
    handleReset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Bulk Bank Upload</DialogTitle>
          <DialogDescription>
            Upload multiple bank accounts at once using CSV file
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Upload CSV */}
        {step === 1 && (
          <div className="space-y-6 py-4">
            {/* Download Template */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-900 mb-2">Step 1: Download Template</h4>
                  <p className="text-sm text-blue-800 mb-3">
                    Download the CSV template and fill in your bank details
                  </p>
                  <Button
                    onClick={handleDownloadTemplate}
                    variant="outline"
                    size="sm"
                    className="bg-white"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download Template
                  </Button>
                </div>
              </div>
            </div>

            {/* Upload CSV */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Upload className="h-5 w-5 text-green-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-green-900 mb-2">Step 2: Upload Filled CSV</h4>
                  <p className="text-sm text-green-800 mb-3">
                    Upload the CSV file with your bank account details
                  </p>
                  <Input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="bg-white"
                  />
                  {file && (
                    <p className="text-sm text-green-700 mt-2">
                      Selected: {file.name}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* CSV Format Info */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2">CSV Format</h4>
              <div className="text-sm text-gray-700 space-y-1">
                <p><strong>Required Columns:</strong></p>
                <ul className="list-disc list-inside ml-2 space-y-1">
                  <li>Bank Name</li>
                  <li>Account Number (digits only)</li>
                  <li>IFSC Code (11 characters)</li>
                  <li>Branch Name</li>
                  <li>Account Holder Name</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Preview */}
        {step === 2 && previewData && (
          <div className="space-y-4 py-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-blue-600 mb-1">Total Rows</div>
                <div className="text-2xl font-bold text-blue-900">{previewData.totalRows}</div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="text-sm text-green-600 mb-1">Valid Banks</div>
                <div className="text-2xl font-bold text-green-900">{previewData.validRows}</div>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="text-sm text-red-600 mb-1">Errors</div>
                <div className="text-2xl font-bold text-red-900">{previewData.errorRows}</div>
              </div>
            </div>

            {/* Valid Banks */}
            {previewData.banks.length > 0 && (
              <div>
                <h4 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5" />
                  Valid Banks ({previewData.banks.length})
                </h4>
                <div className="border rounded-lg overflow-hidden max-h-60 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead>Bank Name</TableHead>
                        <TableHead>Account Number</TableHead>
                        <TableHead>IFSC</TableHead>
                        <TableHead>Branch</TableHead>
                        <TableHead>Account Holder</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.banks.map((bank, index) => (
                        <TableRow key={index}>
                          <TableCell>{bank.bankName}</TableCell>
                          <TableCell>{bank.accountNumber}</TableCell>
                          <TableCell>{bank.ifscCode}</TableCell>
                          <TableCell>{bank.branchName}</TableCell>
                          <TableCell>{bank.accountHolderName}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            {/* Errors */}
            {previewData.errors.length > 0 && (
              <div>
                <h4 className="font-semibold text-red-900 mb-2 flex items-center gap-2">
                  <XCircle className="h-5 w-5" />
                  Errors ({previewData.errors.length})
                </h4>
                <div className="border rounded-lg overflow-hidden max-h-60 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead>Row</TableHead>
                        <TableHead>Errors</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.errors.map((error, index) => (
                        <TableRow key={index}>
                          <TableCell>{error.row}</TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              {error.errors.map((err, i) => (
                                <Badge key={i} variant="destructive" className="mr-1">
                                  {err}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: TPIN Verification */}
        {step === 3 && (
          <div className="space-y-4 py-4">
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-orange-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-orange-900 mb-2">Security Verification</h4>
                  <p className="text-sm text-orange-800 mb-4">
                    You are about to add {previewData?.validRows} bank account(s). 
                    Please enter your TPIN to confirm.
                  </p>
                  
                  <div className="max-w-xs">
                    <Label className="text-base font-medium mb-2 block">Enter TPIN</Label>
                    <div className="relative">
                      <Input
                        type={showTpin ? 'text' : 'password'}
                        placeholder="Enter 6-digit TPIN"
                        value={tpin}
                        onChange={(e) => setTpin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        maxLength="6"
                        className="h-12 text-base pr-12"
                        disabled={loading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowTpin(!showTpin)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showTpin ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          {step === 1 && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={handleUploadAndPreview} disabled={!file || loading}>
                {loading ? 'Processing...' : 'Upload & Preview'}
              </Button>
            </>
          )}

          {step === 2 && (
            <>
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button 
                onClick={handleProceedToTpin} 
                disabled={!previewData || previewData.validRows === 0}
              >
                Proceed to Add ({previewData?.validRows || 0} banks)
              </Button>
            </>
          )}

          {step === 3 && (
            <>
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button 
                onClick={handleSubmit} 
                disabled={!tpin || tpin.length !== 6 || loading}
                className="bg-green-600 hover:bg-green-700"
              >
                {loading ? 'Adding Banks...' : 'Confirm & Add Banks'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
