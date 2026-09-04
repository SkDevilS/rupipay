import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { CheckCircle, XCircle, Clock, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';

export default function ApiResponseDialog({ open, onOpenChange, logs, type = 'payin', error }) {
  if (!logs && !error) return null;

  // Show error if API call failed
  if (error) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="w-5 h-5" />
              Error Loading Transaction Logs
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="font-medium">
                {error}
              </AlertDescription>
            </Alert>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-700 mb-2">Possible reasons:</p>
              <ul className="text-xs text-gray-600 space-y-1 list-disc list-inside">
                <li>Transaction not found in database</li>
                <li>Admin authentication required</li>
                <li>Database connection issue</li>
                <li>Invalid transaction ID format</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const formatJSON = (data) => {
    if (!data) return null;
    if (typeof data === 'string') return data;
    return JSON.stringify(data, null, 2);
  };

  const getStatusIcon = (forwarded) => {
    if (forwarded) {
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    }
    return <XCircle className="w-4 h-4 text-red-500" />;
  };

  const EmptyState = ({ message, icon: Icon = Clock, showNote = true }) => (
    <div className="text-center py-8 text-gray-500">
      <Icon className="w-10 h-10 mx-auto mb-3 opacity-50" />
      <p className="text-sm font-medium">{message}</p>
      {showNote && (
        <p className="text-xs mt-2 text-gray-400">
          This data is not currently stored in the database
        </p>
      )}
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            API Response Details - {logs.transaction_id}
            <Badge variant={
              logs.status === 'SUCCESS' ? 'default' :
              logs.status === 'FAILED' ? 'destructive' :
              'secondary'
            }>
              {logs.status}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Data Availability Info */}
          <Alert className="bg-blue-50 border-blue-200">
            <Info className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-sm">
              <strong className="text-blue-900">Available Data:</strong>
              <div className="mt-2 space-y-1 text-blue-800">
                <div className="flex items-center gap-2">
                  {logs.data_status?.has_request_payload || logs.merchant_request ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <XCircle className="w-3 h-3 text-gray-400" />
                  )}
                  <span className="text-xs">Request Payload (from transaction record)</span>
                </div>
                <div className="flex items-center gap-2">
                  {logs.data_status?.has_gateway_request ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <XCircle className="w-3 h-3 text-gray-400" />
                  )}
                  <span className="text-xs">Gateway Request (not stored)</span>
                </div>
                <div className="flex items-center gap-2">
                  {logs.data_status?.has_gateway_response ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <XCircle className="w-3 h-3 text-gray-400" />
                  )}
                  <span className="text-xs">Gateway Response (not stored)</span>
                </div>
                <div className="flex items-center gap-2">
                  {logs.data_status?.has_callback_data ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <XCircle className="w-3 h-3 text-gray-400" />
                  )}
                  <span className="text-xs">Callback Data (not stored)</span>
                </div>
                <div className="flex items-center gap-2">
                  {logs.callback_to_merchant?.forwarded ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <XCircle className="w-3 h-3 text-gray-400" />
                  )}
                  <span className="text-xs">Callback Forwarded</span>
                </div>
              </div>
            </AlertDescription>
          </Alert>

          {/* Transaction Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Transaction Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Transaction ID</p>
                  <p className="font-mono font-medium text-xs break-all">{logs.transaction_id}</p>
                </div>
                {type === 'payin' ? (
                  <>
                    <div>
                      <p className="text-gray-500">Merchant</p>
                      <p className="font-medium">{logs.merchant_name}</p>
                      <p className="text-xs text-gray-400">{logs.merchant_id}</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <p className="text-gray-500">Payer</p>
                      <p className="font-medium">{logs.payer_name}</p>
                      <p className="text-xs text-gray-400">{logs.payer_type}</p>
                    </div>
                  </>
                )}
                <div>
                  <p className="text-gray-500">Amount</p>
                  <p className="font-semibold">₹{logs.amount?.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Gateway</p>
                  <p className="font-medium">{logs.service_name || logs.pg_partner}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Flow Tabs */}
          <Tabs defaultValue="merchant-request" className="w-full">
            <TabsList className="grid w-full grid-cols-5 h-auto">
              <TabsTrigger value="merchant-request" className="text-xs px-2 py-2 whitespace-normal h-auto min-h-[2.5rem]">
                <span className="block text-center">
                  {type === 'payin' ? 'Merchant Request' : 'Request'}
                </span>
              </TabsTrigger>
              <TabsTrigger value="gateway-request" className="text-xs px-2 py-2 whitespace-normal h-auto min-h-[2.5rem]">
                <span className="block text-center">Gateway Request</span>
              </TabsTrigger>
              <TabsTrigger value="gateway-response" className="text-xs px-2 py-2 whitespace-normal h-auto min-h-[2.5rem]">
                <span className="block text-center">Gateway Response</span>
              </TabsTrigger>
              <TabsTrigger value="callback-received" className="text-xs px-2 py-2 whitespace-normal h-auto min-h-[2.5rem]">
                <span className="block text-center">Callback Received</span>
              </TabsTrigger>
              <TabsTrigger value="callback-forwarded" className="text-xs px-2 py-2 whitespace-normal h-auto min-h-[2.5rem]">
                <span className="flex items-center justify-center gap-1">
                  <span className="block text-center">Callback Sent</span>
                  {logs.callback_to_merchant?.forwarded ? (
                    <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                  )}
                </span>
              </TabsTrigger>
            </TabsList>

            {/* Merchant/Request Payload */}
            <TabsContent value="merchant-request">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    {type === 'payin' ? 'Request from Merchant' : 'Request Payload'}
                  </CardTitle>
                  <p className="text-xs text-gray-500">
                    {type === 'payin' 
                      ? 'The initial request sent by the merchant to create this transaction'
                      : 'The initial request payload for this payout transaction'
                    }
                  </p>
                </CardHeader>
                <CardContent>
                  {(type === 'payin' ? logs.merchant_request : logs.request_payload) ? (
                    <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                      {formatJSON(type === 'payin' ? logs.merchant_request : logs.request_payload)}
                    </pre>
                  ) : (
                    <EmptyState 
                      message="Request data reconstructed from transaction record"
                      icon={Info}
                      showNote={false}
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Gateway Request */}
            <TabsContent value="gateway-request">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    {logs.gateway_request ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-gray-400" />
                    )}
                    Request to Payment Gateway
                  </CardTitle>
                  <p className="text-xs text-gray-500">
                    The request we sent to {logs.service_name || logs.pg_partner}
                  </p>
                </CardHeader>
                <CardContent>
                  {logs.gateway_request ? (
                    <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                      {formatJSON(logs.gateway_request)}
                    </pre>
                  ) : (
                    <EmptyState 
                      message="Gateway request data is not stored in database"
                      icon={AlertTriangle}
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Gateway Response */}
            <TabsContent value="gateway-response">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    {logs.gateway_response ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-gray-400" />
                    )}
                    Response from Payment Gateway
                  </CardTitle>
                  <p className="text-xs text-gray-500">
                    The response received from {logs.service_name || logs.pg_partner}
                  </p>
                </CardHeader>
                <CardContent>
                  {logs.gateway_response ? (
                    <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                      {formatJSON(logs.gateway_response)}
                    </pre>
                  ) : (
                    <EmptyState 
                      message="Gateway response data is not stored in database"
                      icon={AlertTriangle}
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Callback Received */}
            <TabsContent value="callback-received">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    {logs.callback_from_gateway ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-gray-400" />
                    )}
                    Callback from Payment Gateway
                  </CardTitle>
                  <p className="text-xs text-gray-500">
                    The webhook/callback data received from {logs.service_name || logs.pg_partner}
                  </p>
                </CardHeader>
                <CardContent>
                  {logs.callback_from_gateway ? (
                    <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                      {formatJSON(logs.callback_from_gateway)}
                    </pre>
                  ) : (
                    <EmptyState 
                      message="Callback data is not stored in database"
                      icon={Clock}
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Callback Forwarded */}
            <TabsContent value="callback-forwarded">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    {getStatusIcon(logs.callback_to_merchant?.forwarded)}
                    Callback Forwarded to {type === 'payin' ? 'Merchant' : 'Merchant (if applicable)'}
                  </CardTitle>
                  <p className="text-xs text-gray-500">
                    {logs.callback_to_merchant?.forwarded 
                      ? `Callback was forwarded at ${new Date(logs.callback_to_merchant.forwarded_at).toLocaleString()}`
                      : 'Callback has not been forwarded yet'
                    }
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Forwarding Status */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Forwarded</p>
                      <p className="font-medium">
                        {logs.callback_to_merchant?.forwarded ? 'Yes' : 'No'}
                      </p>
                    </div>
                    {logs.callback_to_merchant?.forwarded_at && (
                      <div>
                        <p className="text-gray-500">Forwarded At</p>
                        <p className="font-medium text-xs">
                          {new Date(logs.callback_to_merchant.forwarded_at).toLocaleString()}
                        </p>
                      </div>
                    )}
                    {logs.callback_to_merchant?.merchant_callback_url && (
                      <div className="col-span-2">
                        <p className="text-gray-500">Callback URL</p>
                        <p className="font-mono text-xs break-all">
                          {logs.callback_to_merchant.merchant_callback_url}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Payload Sent */}
                  {logs.callback_to_merchant?.payload_sent && (
                    <div>
                      <p className="text-sm font-medium mb-2 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        Payload Sent to Merchant:
                      </p>
                      <pre className="bg-green-50 border border-green-200 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                        {formatJSON(logs.callback_to_merchant.payload_sent)}
                      </pre>
                    </div>
                  )}

                  {/* Response from Merchant */}
                  {logs.callback_to_merchant?.response && (
                    <div>
                      <p className="text-sm font-medium mb-2 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        Response from Merchant:
                      </p>
                      <pre className="bg-blue-50 border border-blue-200 p-4 rounded-lg overflow-x-auto text-xs font-mono">
                        {formatJSON(logs.callback_to_merchant.response)}
                      </pre>
                    </div>
                  )}

                  {!logs.callback_to_merchant?.forwarded && (
                    <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg">
                      <XCircle className="w-10 h-10 mx-auto mb-3 opacity-50" />
                      <p className="font-medium">Callback Not Forwarded</p>
                      {type === 'payout' && logs.payer_type === 'admin' ? (
                        <p className="text-xs mt-2">Admin payouts do not forward callbacks to merchants</p>
                      ) : (
                        <p className="text-xs mt-2">Callback has not been forwarded to merchant yet</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Additional Information */}
          {logs.additional_info && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Additional Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  {Object.entries(logs.additional_info).map(([key, value]) => (
                    value && (
                      <div key={key}>
                        <p className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                        <p className="font-mono text-xs break-all">{value}</p>
                      </div>
                    )
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
