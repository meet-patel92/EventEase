import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import api from '../api';
import { displayEventTitle } from '../utils/eventTitle';

function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = useCallback(async () => {
    try {
      const response = await api.get('/dashboard/overview/');
      setData(response.data);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || requestError.message || 'Could not load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Fetch live role-scoped aggregates from the dashboard API.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDashboard();
  }, [loadDashboard]);

  if (loading) return <section className="page-container"><h1>Dashboard</h1><p className="loading">Loading dashboard…</p></section>;
  if (error) return <section className="page-container"><h1>Dashboard</h1><div className="error" role="alert">{error}</div><button className="btn btn-primary" onClick={() => { setLoading(true); loadDashboard(); }}>Retry</button></section>;
  if (!data) return null;
  const eventBookings = data.event_bookings?.map((event) => ({ ...event, title: displayEventTitle(event.title) }));

  return (
    <section className="page-container dashboard-page">
      <div className="page-header"><div><p className="eyebrow">Live account overview</p><h1>{data.role} dashboard</h1></div></div>
      <div className="dashboard-card-grid">
        {data.cards.map((card) => (
          <article className="dashboard-card" key={card.key}>
            <span>{card.label}</span>
            <strong>{card.key === 'revenue' ? `₹${card.value}` : card.value}</strong>
          </article>
        ))}
      </div>

      {eventBookings?.length > 0 && (
        <section className="dashboard-panel">
          <h2>Bookings by event</h2>
          <div className="dashboard-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={eventBookings} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="title" tick={{ fill: 'var(--text)' }} />
                <YAxis allowDecimals={false} tick={{ fill: 'var(--text)' }} />
                <Tooltip />
                <Bar dataKey="bookings" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                <Bar dataKey="confirmed" fill="#22c55e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="table-scroll"><table className="data-table"><thead><tr><th>Event</th><th>Date</th><th>Status</th><th>Bookings</th><th>Confirmed</th><th>Tickets</th><th>Revenue</th></tr></thead>
            <tbody>{eventBookings.map((event) => <tr key={event.id}><td>{event.title}</td><td>{event.date}</td><td>{event.status}</td><td>{event.bookings}</td><td>{event.confirmed}</td><td>{event.tickets}</td><td>₹{event.revenue}</td></tr>)}</tbody>
          </table></div>
        </section>
      )}

      {data.upcoming_events?.length > 0 && (
        <section className="dashboard-panel"><h2>Upcoming events</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Event</th><th>Date</th><th>Venue</th><th>Quantity</th><th>Booking</th></tr></thead>
          <tbody>{data.upcoming_events.map((event) => <tr key={event.booking_id}><td>{displayEventTitle(event.event)}</td><td>{event.date}</td><td>{event.venue}</td><td>{event.quantity}</td><td>{event.reference}</td></tr>)}</tbody>
        </table></div></section>
      )}

      {data.recent_bookings?.length > 0 && (
        <section className="dashboard-panel"><h2>Recent bookings</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Reference</th>{data.role === 'ADMIN' && <th>Customer</th>}<th>Event</th><th>Status</th><th>Total</th><th>Date</th></tr></thead>
          <tbody>{data.recent_bookings.map((booking) => <tr key={booking.id}><td>{booking.reference}</td>{data.role === 'ADMIN' && <td>{booking.customer}</td>}<td>{displayEventTitle(booking.event)}</td><td>{booking.status}</td><td>₹{booking.total}</td><td>{new Date(booking.date).toLocaleString()}</td></tr>)}</tbody>
        </table></div></section>
      )}

      <nav className="dashboard-links" aria-label="Dashboard shortcuts">
        <Link to="/bookings" className="btn btn-secondary">Bookings</Link>
        <Link to="/payments" className="btn btn-secondary">Payments</Link>
        <Link to="/tickets" className="btn btn-secondary">Tickets</Link>
        <Link to="/reviews" className="btn btn-secondary">Event reviews</Link>
        {data.role !== 'CUSTOMER' && <Link to="/ticket-scanner" className="btn btn-secondary">Ticket check-in</Link>}
        {data.role === 'ADMIN' && <Link to="/admin/events" className="btn btn-secondary">Events and approvals</Link>}
        {data.role === 'ORGANIZER' && <Link to="/organizer/events" className="btn btn-secondary">Manage my events</Link>}
        {data.role === 'ADMIN' && <Link to="/admin/events" className="btn btn-secondary">Manage event approvals</Link>}
        {data.role === 'ADMIN' && <Link to="/admin/notifications" className="btn btn-secondary">Send customer notification</Link>}
      </nav>
    </section>
  );
}

export default Dashboard;
