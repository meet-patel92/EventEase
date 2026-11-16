import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import ReviewSection from './ReviewSection';
import EventPoster from './EventPoster';
import { displayEventTitle, displayText } from '../utils/eventTitle';

function EventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = Boolean(localStorage.getItem('token'));
  const user = (() => { try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; } })();

  const loadEvent = useCallback(async () => {
    try {
      const response = await api.get(`/events/${id}/`);
      setEvent(response.data);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load this event.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // Load the selected event from the backend, including its current availability.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadEvent();
  }, [loadEvent]);

  const createBooking = async () => {
    if (user?.role !== 'CUSTOMER') {
      setError('Sign in with a customer account to book this event.');
      return;
    }
    setBooking(true);
    setError('');
    try {
      const response = await api.post('/bookings/', { event: Number(id), quantity: Number(quantity) });
      navigate(`/bookings/${response.data.id}`, {
        state: { bookingReference: response.data.booking_reference, bookingStatus: response.data.status },
      });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || Object.values(requestError.response?.data || {}).flat().filter(Boolean).join(' ') || 'Could not create the booking.');
    } finally {
      setBooking(false);
    }
  };

  if (loading) return <section className="page-container"><p className="loading">Loading event…</p></section>;
  if (error && !event) return <section className="page-container"><p className="error" role="alert">{error}</p><Link to="/" className="btn btn-secondary">Back to events</Link></section>;
  if (!event) return null;

  return (
    <section className="page-container event-detail-page">
      <Link to="/" className="btn btn-secondary">← Events</Link>
      <EventPoster className="event-detail-poster" src={event.poster} alt={`${displayEventTitle(event.title)} poster`} />
      <p className="eyebrow">{event.event_date} · {event.start_time}–{event.end_time}</p>
      <h1>{displayEventTitle(event.title)}</h1>
      <p>{event.venue}, {event.city}</p>
      <p>{displayText(event.description)}</p>
      <p className="event-price">₹{event.ticket_price} per ticket</p>
      <p>{event.available_tickets} tickets available</p>
      {user?.role === 'CUSTOMER' && (
        <div className="event-booking-controls">
          <label>Quantity<input type="number" min="1" max={event.available_tickets} value={quantity} onChange={(change) => setQuantity(change.target.value)} /></label>
          <button className="btn btn-primary" onClick={createBooking} disabled={booking || event.available_tickets < 1}>{booking ? 'Reserving…' : 'Reserve tickets'}</button>
        </div>
      )}
      {!isAuthenticated && <Link to="/login" state={{ from: location }} className="btn btn-primary">Sign in to book</Link>}
      {isAuthenticated && user?.role !== 'CUSTOMER' && <p>Booking is available to customer accounts.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <ReviewSection eventId={event.id} />
    </section>
  );
}

export default EventDetail;

