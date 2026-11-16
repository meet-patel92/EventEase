import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';
import { getApiError, getListItems, statusClass } from './eventManagement';
import EventPoster from './EventPoster';
import { displayEventTitle, displayText } from '../utils/eventTitle';

function OrganizerEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const location = useLocation();

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/events/my-events/');
      setEvents(getListItems(response.data, 'my events'));
      setError('');
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load your events.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load organizer-owned events when the management page opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadEvents();
  }, [loadEvents]);

  return (
    <section className="page-container management-page">
      <header className="page-header">
        <div><p className="eyebrow">Organizer workspace</p><h1>My Events</h1></div>
        <Link className="btn btn-primary" to="/organizer/events/new">Create event</Link>
      </header>
      <p>Manage the events you organize and track their approval status.</p>
      {location.state?.notice && <p className="success-message" role="status">{location.state.notice}</p>}
      {loading && <p className="loading" role="status">Loading your events…</p>}
      {!loading && error && <div className="error" role="alert"><p>{error}</p><button className="btn btn-primary" onClick={loadEvents}>Try again</button></div>}
      {!loading && !error && events.length === 0 && (
        <div className="empty-state" role="status"><p>You have not created any events yet.</p><Link className="btn btn-primary" to="/organizer/events/new">Create your first event</Link></div>
      )}
      {!loading && !error && events.length > 0 && (
        <div className="management-list">
          {events.map((event) => (
            <article className="management-card" key={event.id}>
              <EventPoster className="management-poster" src={event.poster} alt={`${displayEventTitle(event.title)} poster`} />
              <div className="management-card-heading">
                <div><h2>{displayEventTitle(event.title)}</h2><p>{event.event_date} · {event.venue}, {event.city}</p></div>
                <span className={statusClass(event.status)}>{event.status}</span>
              </div>
              {event.rejection_reason && <p className="management-rejection"><strong>Rejection reason:</strong> {displayText(event.rejection_reason)}</p>}
              <div className="management-actions">
                <Link className="btn btn-secondary" to={`/organizer/events/${event.id}/edit`}>Edit event</Link>
                {event.status === 'APPROVED' && <>
                  <Link className="btn btn-secondary" to={`/bookings?event=${event.id}`}>Manage bookings</Link>
                  <Link className="btn btn-secondary" to={`/ticket-scanner?event=${event.id}`}>Scan tickets</Link>
                  <Link className="btn btn-secondary" to={`/organizer/events/${event.id}/attendance`}>Attendance report</Link>
                </>}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default OrganizerEvents;

