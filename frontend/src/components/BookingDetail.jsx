import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import PaymentButton from './PaymentButton';
import EventPoster from './EventPoster';
import { displayBookingReference, displayEventTitle } from '../utils/eventTitle';

function BookingDetail() {
  const { id } = useParams();
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cancelMessage, setCancelMessage] = useState('');
  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; } })();

  const loadBooking = useCallback(async () => {
    try {
      const response = await api.get(`/bookings/${id}/`);
      setBooking(response.data);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Could not load this booking.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // The detail request is asynchronous and populates the page after the response.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadBooking();
  }, [loadBooking]);

  const cancelBooking = async () => {
    try {
      setCancelMessage('');
      await api.post(`/bookings/${id}/cancel/`);
      setCancelMessage('Booking cancelled and reserved tickets released.');
      setLoading(true);
      await loadBooking();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Could not cancel this booking.');
    }
  };

  if (loading) return <div className="page-container"><h1>Booking details</h1><p className="loading">Loading booking…</p></div>;
  if (error && !booking) return <div className="page-container"><h1>Booking details</h1><p className="error" role="alert">{error}</p><Link to="/bookings" className="btn btn-secondary">Back to bookings</Link></div>;
  if (!booking) return null;

  const canManage = booking.customer === user?.id && user?.role === 'CUSTOMER';

  return (
    <section className="page-container booking-detail-page">
      <div className="page-header">
        <div><p className="eyebrow">Booking reference {displayBookingReference(booking.booking_reference)}</p><h1>{displayEventTitle(booking.event_title)}</h1></div>
        <Link to="/bookings" className="btn btn-secondary">Back to bookings</Link>
      </div>
      <EventPoster className="booking-detail-poster" src={booking.event_poster} alt={`${displayEventTitle(booking.event_title)} poster`} />
      {cancelMessage && <p className="booking-confirmation" role="status">{cancelMessage}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="booking-detail-grid">
        <div><span>Booking ID</span><strong>{booking.id}</strong></div>
        <div><span>Event date</span><strong>{booking.event_date}</strong></div>
        <div><span>Time</span><strong>{booking.start_time} – {booking.end_time}</strong></div>
        <div><span>Venue</span><strong>{booking.venue}, {booking.city}</strong></div>
        <div><span>Ticket quantity</span><strong>{booking.quantity}</strong></div>
        <div><span>Unit price</span><strong>₹{booking.unit_price}</strong></div>
        <div><span>Total</span><strong>₹{booking.total_amount}</strong></div>
        <div><span>Status</span><strong className={`status-badge ${booking.status.toLowerCase()}`}>{booking.status}</strong></div>
        {booking.customer_email && <div><span>Customer</span><strong>{booking.customer_email}</strong></div>}
        <div><span>Booked</span><strong>{new Date(booking.booking_date).toLocaleString()}</strong></div>
      </div>
      {canManage && booking.status === 'PENDING' && (
        <div className="booking-actions">
          <PaymentButton booking={booking} onVerified={() => setCancelMessage('Payment verified. Tickets are being issued.')} />
          <button className="btn btn-secondary" onClick={cancelBooking}>Cancel booking</button>
        </div>
      )}
      {canManage && booking.status === 'CONFIRMED' && <Link to="/tickets" className="btn btn-primary">View tickets</Link>}
    </section>
  );
}

export default BookingDetail;

