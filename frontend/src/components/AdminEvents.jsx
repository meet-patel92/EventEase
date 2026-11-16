import { useEffect, useState } from 'react';
import api from '../api';
import { getApiError, getAllEvents, statusClass } from './eventManagement';
import EventPoster from './EventPoster';
import { displayCategoryName, displayEventTitle, displayText } from '../utils/eventTitle';

function AdminEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reasons, setReasons] = useState({});
  const [confirmation, setConfirmation] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadEvents = async () => {
    setLoading(true);
    try {
      setEvents(await getAllEvents());
      setError('');
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load events for review.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // The admin API list is paginated; load all pages before filtering pending items.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadEvents();
  }, []);

  const pendingEvents = events.filter((event) => event.status === 'PENDING');

  const requestAction = (event, action) => {
    const reason = reasons[event.id]?.trim() || '';
    if (action === 'reject' && !reason) {
      setError('Enter a rejection reason before continuing.');
      return;
    }
    setError('');
    setConfirmation({ event, action, reason });
  };

  const confirmAction = async () => {
    if (!confirmation) return;
    const { event, action, reason } = confirmation;
    setSaving(true);
    setError('');
    try {
      await api.patch(`/events/${event.id}/${action}/`, action === 'reject'
        ? { status: 'REJECTED', rejection_reason: reason }
        : {});
      setNotice(`${displayEventTitle(event.title)} was ${action === 'approve' ? 'approved' : 'rejected'}.`);
      setConfirmation(null);
      await loadEvents();
    } catch (requestError) {
      setError(getApiError(requestError, `Could not ${action} this event.`));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-container management-page">
      <header className="page-header"><div><p className="eyebrow">Administrator workspace</p><h1>Event Management</h1></div><button className="btn btn-secondary" onClick={loadEvents} disabled={loading}>Refresh</button></header>
      <p>Review pending submissions and inspect event details before deciding.</p>
      {notice && <p className="success-message" role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {loading && <p className="loading" role="status">Loading events for review…</p>}
      {!loading && !error && pendingEvents.length === 0 && <p className="empty-state" role="status">There are no pending events to review.</p>}
      {!loading && pendingEvents.length > 0 && (
        <div className="management-list">
          {pendingEvents.map((event) => (
            <article className="management-card" key={event.id}>
              <div className="management-card-heading"><div><h2>{displayEventTitle(event.title)}</h2><p>{event.event_date} · {event.venue}, {event.city}</p></div><span className={statusClass(event.status)}>{event.status}</span></div>
              <details className="management-details"><summary>View event details</summary>
                <EventPoster className="management-poster" src={event.poster} alt={`${displayEventTitle(event.title)} poster`} />
                <dl className="management-detail-grid"><div><dt>Organizer</dt><dd>{event.organizer_email || event.organizer}</dd></div><div><dt>Category</dt><dd>{displayCategoryName(event.category_name || 'Uncategorized')}</dd></div><div><dt>Time</dt><dd>{event.start_time}–{event.end_time}</dd></div><div><dt>Price</dt><dd>₹{event.ticket_price}</dd></div><div><dt>Tickets</dt><dd>{event.available_tickets} available of {event.total_tickets}</dd></div></dl>
                <p>{displayText(event.description)}</p>{event.address && <p>{displayText(event.address)}</p>}
              </details>
              <label className="management-reason">Rejection reason<textarea aria-label={`Rejection reason for ${displayEventTitle(event.title)}`} rows="2" value={reasons[event.id] || ''} onChange={(change) => setReasons((current) => ({ ...current, [event.id]: change.target.value }))} /></label>
              <div className="management-actions"><button className="btn btn-primary" onClick={() => requestAction(event, 'approve')}>Approve</button><button className="btn btn-danger" onClick={() => requestAction(event, 'reject')}>Reject</button></div>
            </article>
          ))}
        </div>
      )}
      {confirmation && (
        <div className="management-modal-backdrop" role="presentation">
          <section className="management-modal" role="dialog" aria-modal="true" aria-labelledby="management-confirm-title">
            <h2 id="management-confirm-title">Confirm {confirmation.action === 'approve' ? 'approval' : 'rejection'}</h2>
            <p>{confirmation.action === 'approve' ? `Approve “${displayEventTitle(confirmation.event.title)}”?` : `Reject “${displayEventTitle(confirmation.event.title)}” with this reason: ${confirmation.reason}`}</p>
            <div className="management-actions"><button className="btn btn-primary" onClick={confirmAction} disabled={saving}>{saving ? 'Saving…' : 'Confirm'}</button><button className="btn btn-secondary" onClick={() => setConfirmation(null)} disabled={saving}>Cancel</button></div>
          </section>
        </div>
      )}
    </section>
  );
}

export default AdminEvents;

