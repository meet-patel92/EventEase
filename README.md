# EventEase – Event Management & Online Ticket Booking System

EventEase is a full-stack web application designed to simplify event discovery, event management, online booking, and ticket handling. It provides separate experiences for customers, organizers, and administrators.

## Project Overview

EventEase allows users to explore events, book tickets, manage bookings, and access digital entry passes. Organizers can create and manage events, while administrators can oversee platform activities.

## Key Features

### Customer
- User registration and secure login
- Browse and explore available events
- View event details and ticket availability
- Book event tickets online
- View and manage bookings
- Access digital tickets with QR codes
- Receive notifications
- Submit reviews for eligible events

### Organizer
- Create and manage events
- Upload event posters
- Manage event information and ticket availability
- View event bookings
- Scan ticket check-in codes
- Monitor event attendance

### Administrator
- Admin dashboard
- Manage platform events
- Manage users and platform activities
- Send notifications to customers
- Monitor event-related information

### Ticket & Payment Management
- Digital ticket generation
- QR-based ticket verification
- Ticket check-in functionality
- Razorpay test-mode payment configuration

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, JavaScript, HTML, CSS |
| Backend | Python, Django |
| API | Django REST Framework |
| Database | MySQL |
| Authentication | JWT |
| Payment | Razorpay Test Mode |
| Testing | Pytest, Playwright |
| Development Tools | VS Code, Git, GitHub |

## Project Structure

```text
EventEase/
│
├── backend/
│   ├── accounts/
│   ├── bookings/
│   ├── config/
│   ├── dashboard/
│   ├── events/
│   ├── notifications/
│   ├── payments/
│   ├── reviews/
│   ├── tickets/
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── e2e/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── docs/
├── .gitignore
└── README.md
```

## Installation and Setup

### Prerequisites

Install the following before running the project:

- Python 3.12
- Node.js and npm
- MySQL Server 8.0
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/meet-patel92/EventEase.git
cd EventEase
```

### 2. Backend Setup

Create and activate a Python virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Create your local environment file:

```bash
copy backend\.env.example backend\.env
```

Update `backend/.env` with your local MySQL database credentials and other required configuration.

Create the MySQL database named `eventease_db` before running migrations.

Run database migrations:

```bash
cd backend
python manage.py migrate
```

Start the Django development server:

```bash
python manage.py runserver 127.0.0.1:8000
```

Backend API:

`http://127.0.0.1:8000/api/v1/`

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend application:

`http://localhost:5173`

## Testing

Backend tests and frontend end-to-end tests are included in the project.

- Backend: Django and API tests
- Frontend: Playwright end-to-end tests
- Responsive UI verification

Run tests using the project's configured test environment and follow the testing documentation in the `docs/` directory.

## Documentation

Additional project documentation is available in the `docs/` folder:

- API Reference
- Project Documentation
- Installation and Setup Guide
- User and Admin Manual
- Testing and QA Report
- Database and System Diagrams

## Security Notes

- Never upload `.env` files or real credentials.
- Use your own local database credentials.
- Keep Razorpay credentials private.
- Use Razorpay test credentials for payment testing.
- Do not use production credentials in development.

## Future Enhancements

- Production payment gateway integration
- Advanced event analytics
- Improved event recommendation system
- Additional notification options
- Deployment to a cloud hosting platform
  
## Author

**Meet Patel**

GitHub: https://github.com/meet-patel92

---

**EventEase – Make Every Event Memorable!**
