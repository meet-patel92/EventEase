import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api';
import EventPoster from './EventPoster';
import { displayBookingReference, displayEventTitle } from '../utils/eventTitle';

const statuses = ['PENDING', 'CONFIRMED', 'CANCELLED', 'EXPIRED'];

function BookingList() {
  const [searchParams] = useSearchParams();
  const eventId = searchParams.get('event');
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const loadBookings = useCallback(async () => {
    try {
      const response = await api.get('/bookings/', {
        params: { page, search: search || undefined, status: statusFilter || undefined, event: eventId || undefined },
      });
      const data = response.data;
      const results = Array.isArray(data) ? data : data?.results;
      if (!Array.isArray(results)) throw new Error('The bookings service returned an unexpected response.');
      setBookings(results);
      setCount(Array.isArray(data) ? results.length : data.count || 0);
      setHasNext(!Array.isArray(data) && Boolean(data.next));
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || requestError.message || 'Could not load bookings.');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, eventId]);

  useEffect(() => {
    // Initial request synchronizes this page with the API's scoped booking list.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadBookings();
  }, [loadBookings]);

  const submitSearch = (event) => {
    event.preventDefault();
    setLoading(true);
    setPage(1);
    setSearch(searchInput.trim());
  };

  const changeStatus = (event) => {
    setLoading(true);
    setPage(1);
    setStatusFilter(event.target.value);
  };

  const cancelBooking = async (bookingId) => {
    try {
      setError('');
      await api.post(`/bookings/${bookingId}/cancel/`);
      setLoading(true);
      await loadBookings();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Could not cancel this booking.');
    }
  };

  return (
    <section className="page-container booking-management">
      <div className="page-header">
        <div>
          <p className="eyebrow">Your EventEase activity</p>
          <h1>Bookings</h1>
        </div>
        <Link to="/payments" className="btn btn-secondary">Payment history</Link>
      </div>

      <div className="booking-filters">
        <form onSubmit={submitSearch} className="booking-search">
          <label htmlFor="booking-search">Search bookings</label>
          <input id="booking-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Reference or event name" />
          <button className="btn btn-primary" type="submit">Search</button>
        </form>
        <label className="booking-status-filter" htmlFor="booking-status">Status
          <select id="booking-status" value={statusFilter} onChange={changeStatus}>
            <option value="">All statuses</option>
            {statuses.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {loading && <p className="loading" role="status">Loading bookings…</p>}
      {!loading && !error && bookings.length === 0 && (
        <div className="empty-state booking-empty">
          <p>No bookings found.</p>
          <Link to="/" className="btn btn-primary">Explore Events</Link>
        </div>
      )}

      {!loading && bookings.length > 0 && (
        <>
          <div className="booking-grid">
            {bookings.map((booking) => (
              <article className="booking-card" key={booking.id}>
                <EventPoster className="booking-poster" src={booking.event_poster} alt={`${displayEventTitle(booking.event_title)} poster`} />
                <div className="booking-card-body">
                  <div className="booking-card-heading">
                    <div><p className="event-date">{booking.event_date}</p><h2>{displayEventTitle(booking.event_title)}</h2></div>
                    <span className={`status-badge ${booking.status.toLowerCase()}`}>{booking.status}</span>
                  </div>
                  <p>{booking.venue}{booking.city ? ` · ${booking.city}` : ''}</p>
                  <div className="booking-facts">
                    <span>Reference <strong>{displayBookingReference(booking.booking_reference)}</strong></span>
                    <span>Tickets <strong>{booking.quantity}</strong></span>
                    <span>Total <strong>₹{booking.total_amount}</strong></span>
                    {booking.customer_email && <span>Customer <strong>{booking.customer_email}</strong></span>}
                  </div>
                  <div className="ticket-actions">
                    <Link to={`/bookings/${booking.id}`} className="btn btn-secondary">Details</Link>
                    {booking.status === 'PENDING' && (
                      <Link to={`/bookings/${booking.id}`} className="btn btn-primary">Continue to payment</Link>
                    )}
                    {booking.status === 'PENDING' && (
                      <button className="btn btn-download" onClick={() => cancelBooking(booking.id)}>Cancel booking</button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
          <div className="pagination-controls">
            <button className="btn btn-secondary" disabled={page <= 1} onClick={() => { setLoading(true); setPage((current) => current - 1); }}>Previous</button>
            <span>{count} booking{count === 1 ? '' : 's'}</span>
            <button className="btn btn-secondary" disabled={!hasNext} onClick={() => { setLoading(true); setPage((current) => current + 1); }}>Next</button>
          </div>
        </>
      )}
      {!loading && error && <button className="btn btn-primary" onClick={() => { setLoading(true); loadBookings(); }}>Retry</button>}
    </section>
  );
}

export default BookingList;

