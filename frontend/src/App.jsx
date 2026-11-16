import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { Bell, CalendarDays, LayoutDashboard, LogIn, LogOut, Menu, Ticket, X, Sparkles } from 'lucide-react';
import './App.css';
import api from './api';
const EventList = lazy(() => import('./components/EventList'));
const EventDetail = lazy(() => import('./components/EventDetail'));
const Login = lazy(() => import('./components/Login'));
const Register = lazy(() => import('./components/Register'));
const BookingList = lazy(() => import('./components/BookingList'));
const BookingDetail = lazy(() => import('./components/BookingDetail'));
const PaymentHistory = lazy(() => import('./components/PaymentHistory'));
const Dashboard = lazy(() => import('./components/Dashboard'));
const TicketScanner = lazy(() => import('./components/TicketScanner'));
const TicketList = lazy(() => import('./components/TicketList'));
const TicketDetail = lazy(() => import('./components/TicketDetail'));
const NotificationList = lazy(() => import('./components/NotificationList'));
const OrganizerEvents = lazy(() => import('./components/OrganizerEvents'));
const EventForm = lazy(() => import('./components/EventForm'));
const AdminEvents = lazy(() => import('./components/AdminEvents'));
const AdminSendNotification = lazy(() => import('./components/AdminSendNotification'));
const ReviewList = lazy(() => import('./components/ReviewList'));
const AttendanceReport = lazy(() => import('./components/AttendanceReport'));

function ProtectedRoute({ children, allowedRoles }) {
  const location = useLocation();
  const isAuthenticated = Boolean(localStorage.getItem('token'));
  let user = null;
  try { user = JSON.parse(localStorage.getItem('user') || 'null'); } catch { /* malformed session is unauthorized */ }

  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return (
      <section className="page-container access-denied" role="alert">
        <p className="eyebrow">Restricted area</p>
        <h1>Access denied</h1>
        <p>You do not have permission to access this page.</p>
        <Link to="/dashboard" className="btn btn-secondary">Return to dashboard</Link>
      </section>
    );
  }
  return children;
}

function AppLayout() {
  const isAuthenticated = Boolean(localStorage.getItem('token'));
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  let user = null;
  try { user = JSON.parse(localStorage.getItem('user') || 'null'); } catch { /* malformed session */ }
  const role = user?.role;

  useEffect(() => {
    if (!isAuthenticated) {
      return undefined;
    }
    let active = true;
    api.get('/notifications/unread-count/').then(({ data }) => {
      if (active) setUnreadCount(data.unread_count || 0);
    }).catch(() => {
      if (active) setUnreadCount(0);
    });
    const handleUnreadCount = (event) => setUnreadCount(event.detail);
    window.addEventListener('notifications:unread-count', handleUnreadCount);
    return () => {
      active = false;
      window.removeEventListener('notifications:unread-count', handleUnreadCount);
    };
  }, [isAuthenticated, location.pathname]);

  return (
      <div className="app">
        <nav className="navbar" aria-label="Main navigation">
          <div className="navbar-inner">
            <Link to="/" className="navbar-logo" aria-label="Brand"><span className="brand-mark"><Sparkles size={19} /></span><span>EventEase</span></Link>
            <button className="nav-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? <X size={21} /> : <Menu size={21} />}</button>
            <div className={`navbar-content${menuOpen ? ' is-open' : ''}`} onClick={() => setMenuOpen(false)}>
              <div className="navbar-menu">
                <Link to="/" aria-label="Home" className={`nav-link${location.pathname === '/' ? ' active' : ''}`}><CalendarDays size={16} />Explore</Link>
                {isAuthenticated && role === 'CUSTOMER' && <Link to="/tickets" className="nav-link"><Ticket size={16} />My tickets</Link>}
                {isAuthenticated && <Link to="/dashboard" className="nav-link"><LayoutDashboard size={16} />Dashboard</Link>}
                {isAuthenticated && role === 'CUSTOMER' && <Link to="/bookings" className="nav-link">Bookings</Link>}
                {isAuthenticated && <Link to="/notifications" className="nav-link nav-notifications"><Bell size={16} />Notifications{unreadCount > 0 && <span className="unread-count" aria-label={`${unreadCount} unread notifications`}>{unreadCount > 99 ? '99+' : unreadCount}</span>}</Link>}
                {isAuthenticated && role !== 'ADMIN' && <Link to="/reviews" className="nav-link">Reviews</Link>}
                {isAuthenticated && role === 'ORGANIZER' && <Link to="/organizer/events" className="nav-link">My events</Link>}
                {isAuthenticated && role === 'ORGANIZER' && <Link to="/ticket-scanner" className="nav-link">Check-in</Link>}
                {isAuthenticated && role === 'ADMIN' && <Link to="/admin/events" className="nav-link">Event approvals</Link>}
                {isAuthenticated && role === 'ADMIN' && <Link to="/admin/notifications" className="nav-link">Send notification</Link>}
                {isAuthenticated && role === 'ADMIN' && <Link to="/ticket-scanner" className="nav-link">Ticket scanner</Link>}
              </div>
              <div className="navbar-user">
                {isAuthenticated ? <><span className="user-greeting"><span>Welcome</span>, <strong>{user?.first_name || user?.username || 'there'}</strong></span><button className="btn btn-logout" onClick={() => { localStorage.removeItem('token'); localStorage.removeItem('user'); window.location.href = '/'; }}><LogOut size={16} />Logout</button></> : <><Link to="/login" className="nav-link"><LogIn size={16} />Sign in</Link><Link to="/register" className="btn btn-primary nav-register">Create account</Link></>}
              </div>
            </div>
          </div>
        </nav>

        <main>
          <Suspense fallback={<p className="page-loading" role="status">Loading page…</p>}>
          <Routes>
            <Route path="/" element={
              <EventList />
            } />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/bookings" element={<ProtectedRoute><BookingList /></ProtectedRoute>} />
            <Route path="/bookings/:id" element={<ProtectedRoute><BookingDetail /></ProtectedRoute>} />
            <Route path="/payments" element={<ProtectedRoute><PaymentHistory /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/organizer/events" element={<ProtectedRoute allowedRoles={['ORGANIZER']}><OrganizerEvents /></ProtectedRoute>} />
            <Route path="/organizer/events/new" element={<ProtectedRoute allowedRoles={['ORGANIZER']}><EventForm /></ProtectedRoute>} />
            <Route path="/organizer/events/:id/edit" element={<ProtectedRoute allowedRoles={['ORGANIZER']}><EventForm /></ProtectedRoute>} />
            <Route path="/organizer/events/:id/attendance" element={<ProtectedRoute allowedRoles={['ORGANIZER']}><AttendanceReport /></ProtectedRoute>} />
            <Route path="/admin/events" element={<ProtectedRoute allowedRoles={['ADMIN']}><AdminEvents /></ProtectedRoute>} />
            <Route path="/admin/notifications" element={<ProtectedRoute allowedRoles={['ADMIN']}><AdminSendNotification /></ProtectedRoute>} />
            <Route path="/ticket-scanner" element={<ProtectedRoute allowedRoles={['ADMIN', 'ORGANIZER']}><TicketScanner /></ProtectedRoute>} />
            <Route path="/notifications" element={<ProtectedRoute><NotificationList /></ProtectedRoute>} />
            <Route path="/reviews" element={<ProtectedRoute><ReviewList /></ProtectedRoute>} />
            <Route path="/tickets" element={<ProtectedRoute><TicketList /></ProtectedRoute>} />
            <Route path="/tickets/:id" element={<ProtectedRoute><TicketDetail /></ProtectedRoute>} />
          </Routes>
          </Suspense>
        </main>
        {location.pathname === '/' && <footer className="site-footer"><div className="footer-inner"><Link to="/" className="footer-brand">EventEase</Link><p>Find your people. Make a day of it.</p><span>© {new Date().getFullYear()} EventEase</span></div></footer>}
      </div>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
