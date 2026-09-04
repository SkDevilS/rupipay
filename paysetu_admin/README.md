# Moneyone - Payment Dashboard

A modern, feature-rich payment dashboard built with React, Vite, and Tailwind CSS for managing payin/payout transactions.

## Features

### 1. Dashboard
- Settled, Unsettled, and Total Amount overview
- Payin/Payout statistics (Today, Yesterday, Last 7 days, Last 30 days)
- Transaction status breakdown (Success, Pending, Failed)
- Custom date range filtering

### 2. User Management
- **User Onboarding**: Add new users with complete business details
- **User List**: View and manage all registered users
- **Service Routing**: Configure payment gateway routing and priorities
- **OTP Service**: Manage OTP configuration and testing

### 3. Transactions
- **Payin Report**: Detailed payin transaction history with filters
- **Payout Report**: Comprehensive payout transaction records
- **Pending Payin**: Monitor pending payin transactions
- **Pending Payout**: Track pending payout requests

### 4. Wallet
- **Wallet Statement**: Complete transaction history with credit/debit details
- **Unsettled Wallet**: View and settle unsettled transactions

### 5. Fund Manager
- **Topup Fund**: Request fund topup with proof upload
- **Fund Settlement**: Process merchant settlements
- **Fetch Fund**: Withdraw funds to bank account
- **Fund Requests**: Manage all fund-related requests

### 6. Security
- **Change Password**: Update account password with validation
- **Change PIN**: Modify transaction PIN (6-digit)

### 7. Settings
- **Bank Management**: Add/Update bank account details
- **Manage Services**: Enable/Disable payment services
- **Commercials**: Configure service charges and view revenue

### 8. Activity Logs
- Complete audit trail of all system activities
- Filter by date range and search functionality
- Export logs for compliance

## Tech Stack

- **React 19** - UI library
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router DOM** - Routing
- **Radix UI** - Accessible components
- **Lucide React** - Icons
- **Recharts** - Charts (optional)

## Installation

1. Navigate to the project directory:
```bash
cd moneyone
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and visit:
```
http://localhost:5173
```

## Build for Production

```bash
npm run build
```

The production-ready files will be in the `dist` directory.

## Project Structure

```
moneyone/
├── src/
│   ├── components/
│   │   └── ui/          # Reusable UI components
│   ├── layout/
│   │   └── DashboardLayout.jsx
│   ├── lib/
│   │   └── utils.js     # Utility functions
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Login.jsx
│   │   ├── User/        # User management pages
│   │   ├── Transactions/ # Transaction pages
│   │   ├── Wallet/      # Wallet pages
│   │   ├── FundManager/ # Fund management pages
│   │   ├── Security/    # Security pages
│   │   ├── Settings/    # Settings pages
│   │   └── ActivityLogs.jsx
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── public/
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

## Default Login

For development purposes, any email/password combination will work. In production, implement proper authentication.

## Features Highlights

- **Modern UI**: Clean, gradient-based design with smooth animations
- **Responsive**: Works seamlessly on desktop, tablet, and mobile
- **Dark Sidebar**: Professional gradient sidebar with collapsible menu
- **Real-time Stats**: Mock data showing transaction statistics
- **Export Functionality**: Export reports and logs
- **Filter Options**: Date range and search filters across pages
- **Status Indicators**: Color-coded status badges for quick identification

## Customization

### Colors
Edit `tailwind.config.js` and `src/index.css` to customize the color scheme.

### Mock Data
Replace mock data in individual page files with actual API calls.

### API Integration
Add API service files in `src/api/` directory and integrate with pages.

## Future Enhancements

- Real-time notifications
- Advanced analytics and charts
- Multi-language support
- Role-based access control
- API documentation
- Automated testing

## License

MIT License - feel free to use this project for your needs.

## Support

For issues or questions, please create an issue in the repository.
