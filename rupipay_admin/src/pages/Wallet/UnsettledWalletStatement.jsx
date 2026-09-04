import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Wallet, Download, Search } from 'lucide-react'
import { toast } from 'sonner'

const mockTransactions = [
  { 
    id: 1,
    merchantId: 'Jss Money Admin 10000',
    transactionType: 'Payin',
    particulars: 'Settlement Pending',
    date: '14-01-2026 15:30:45',
    transAmount: 250000.00,
    transactionId: 'UST1768445892',
    openingBalance: 500000.00,
    crDrAmount: 250000.00,
    closingBalance: 750000.00,
    commissionRate: 2500.00,
    tds: 450.00,
    debitCredit: 'Credit',
    remarks: 'Awaiting settlement',
    transactionStatus: 'PENDING',
    impactUser: 'Paymique Studios Private limited',
    checkStatus: 'Check'
  },
  { 
    id: 2,
    merchantId: 'Tech Solutions 20000',
    transactionType: 'Payout',
    particulars: 'Refund Pending',
    date: '13-01-2026 10:15:20',
    transAmount: 150000.00,
    transactionId: 'UST1768334521',
    openingBalance: 750000.00,
    crDrAmount: -150000.00,
    closingBalance: 600000.00,
    commissionRate: 1500.00,
    tds: 270.00,
    debitCredit: 'Debit',
    remarks: 'Refund processing',
    transactionStatus: 'PENDING',
    impactUser: 'Digital Services Ltd',
    checkStatus: 'Check'
  },
]

export default function UnsettledWalletStatement() {
  const [searchFilter, setSearchFilter] = useState('Date')
  const [fromDate, setFromDate] = useState('2026-01-01')
  const [toDate, setToDate] = useState('2026-01-14')
  const [transactions, setTransactions] = useState(mockTransactions)
  const [showFilters, setShowFilters] = useState(false)
  const [entriesPerPage, setEntriesPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  const handleSearch = () => {
    toast.success('Search applied successfully!')
  }

  const handleReset = () => {
    setFromDate('2026-01-01')
    setToDate('2026-01-14')
    setSearchTerm('')
    toast.info('Filters reset')
  }

  const handleExport = () => {
    toast.success('Report exported successfully!')
  }

  const handleCheckStatus = (txn) => {
    toast.info(`Checking status for transaction ${txn.transactionId}`)
  }

  const filteredTransactions = transactions.filter(txn => {
    if (!searchTerm) return true
    return (
      txn.merchantId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      txn.transactionId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      txn.impactUser.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })

  // Pagination calculations
  const totalPages = Math.ceil(filteredTransactions.length / entriesPerPage)
  const startIndex = (currentPage - 1) * entriesPerPage
  const endIndex = startIndex + entriesPerPage
  const currentTransactions = filteredTransactions.slice(startIndex, endIndex)

  const handlePageChange = (page) => {
    setCurrentPage(page)
  }

  const handlePrevious = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const handleNext = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header with Export and Search Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wallet className="h-8 w-8 text-orange-600" />
          <h1 className="text-3xl font-bold">Unsettled Wallet Statement</h1>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleExport}
            className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button
            onClick={() => setShowFilters(!showFilters)}
            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
          >
            <Search className="h-4 w-4 mr-2" />
            {showFilters ? 'Hide Filters' : 'Search'}
          </Button>
        </div>
      </div>

      {/* Search Filters - Hidden by default */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle>Search Filters :</CardTitle>
          </CardHeader>
          <CardContent>
            {/* All filters in one horizontal row with proper alignment */}
            <div className="grid grid-cols-12 gap-4 items-end">
              <div className="col-span-2">
                <Label className="text-sm font-medium">Filter Type</Label>
                <select
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="Date">Date</option>
                  <option value="Transaction ID">Transaction ID</option>
                  <option value="Merchant ID">Merchant ID</option>
                  <option value="Status">Status</option>
                </select>
              </div>
              <div className="col-span-3">
                <Label className="text-sm font-medium">From Date</Label>
                <Input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="h-9"
                />
              </div>
              <div className="col-span-3">
                <Label className="text-sm font-medium">To Date</Label>
                <Input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="h-9"
                />
              </div>
              <div className="col-span-2">
                <Button 
                  onClick={handleSearch}
                  className="w-full h-9 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
                >
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>
              <div className="col-span-2">
                <Button 
                  onClick={handleReset}
                  variant="outline"
                  className="w-full h-9"
                >
                  Reset
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transaction Table */}
      <Card>
        <CardContent className="pt-6">
          {/* Table Controls */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm">Show</span>
              <select
                value={entriesPerPage}
                onChange={(e) => setEntriesPerPage(Number(e.target.value))}
                className="flex h-9 w-20 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm">entries</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm">Search:</span>
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64 h-9"
                placeholder="Search..."
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50">
                  <TableHead className="font-semibold">MERCHANT ID</TableHead>
                  <TableHead className="font-semibold">TRANSACTION TYPE</TableHead>
                  <TableHead className="font-semibold">PARTICULARS</TableHead>
                  <TableHead className="font-semibold">DATE</TableHead>
                  <TableHead className="font-semibold">TRANS. AMOUNT</TableHead>
                  <TableHead className="font-semibold">TRANSACTION ID</TableHead>
                  <TableHead className="font-semibold">OPENING BALANCE</TableHead>
                  <TableHead className="font-semibold">CR. / DR. AMOUNT</TableHead>
                  <TableHead className="font-semibold">CLOSING BALANCE</TableHead>
                  <TableHead className="font-semibold">COMMISSION/ CHARGES RATE</TableHead>
                  <TableHead className="font-semibold">TDS</TableHead>
                  <TableHead className="font-semibold">DEBIT/CREDIT</TableHead>
                  <TableHead className="font-semibold">REMARKS</TableHead>
                  <TableHead className="font-semibold">TRANSACTION STATUS</TableHead>
                  <TableHead className="font-semibold">IMPACT USER</TableHead>
                  <TableHead className="font-semibold">CHECK STATUS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransactions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={16} className="text-center py-8 text-gray-500">
                      No unsettled transactions found
                    </TableCell>
                  </TableRow>
                ) : (
                  currentTransactions.map((txn) => (
                    <TableRow key={txn.id} className="hover:bg-gray-50">
                      <TableCell className="font-medium">{txn.merchantId}</TableCell>
                      <TableCell>{txn.transactionType}</TableCell>
                      <TableCell>{txn.particulars}</TableCell>
                      <TableCell className="whitespace-nowrap">{txn.date}</TableCell>
                      <TableCell className="font-medium">₹{txn.transAmount.toLocaleString()}</TableCell>
                      <TableCell className="font-mono text-xs">{txn.transactionId}</TableCell>
                      <TableCell>₹{txn.openingBalance.toLocaleString()}</TableCell>
                      <TableCell className={txn.crDrAmount < 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
                        {txn.crDrAmount < 0 ? '-' : '+'}₹{Math.abs(txn.crDrAmount).toLocaleString()}
                      </TableCell>
                      <TableCell>₹{txn.closingBalance.toLocaleString()}</TableCell>
                      <TableCell>₹{txn.commissionRate.toLocaleString()}</TableCell>
                      <TableCell>₹{txn.tds.toLocaleString()}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          txn.debitCredit === 'Debit' 
                            ? 'bg-red-100 text-red-700' 
                            : 'bg-green-100 text-green-700'
                        }`}>
                          {txn.debitCredit}
                        </span>
                      </TableCell>
                      <TableCell>{txn.remarks}</TableCell>
                      <TableCell>
                        <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
                          {txn.transactionStatus}
                        </span>
                      </TableCell>
                      <TableCell>{txn.impactUser}</TableCell>
                      <TableCell>
                        {txn.checkStatus && (
                          <Button
                            size="sm"
                            onClick={() => handleCheckStatus(txn)}
                            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-xs h-7"
                          >
                            {txn.checkStatus}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <div className="text-sm text-gray-600">
              Showing {startIndex + 1} to {Math.min(endIndex, filteredTransactions.length)} of {filteredTransactions.length} entries
            </div>
            <div className="flex gap-1">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handlePrevious}
                disabled={currentPage === 1}
                className="text-sm"
              >
                Previous
              </Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePageChange(page)}
                  className={`text-sm ${
                    currentPage === page 
                      ? 'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800' 
                      : ''
                  }`}
                >
                  {page}
                </Button>
              ))}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleNext}
                disabled={currentPage === totalPages}
                className="text-sm"
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
