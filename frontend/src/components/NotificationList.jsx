import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import { displayText, isInternalDemoNotification } from '../utils/eventTitle';

function NotificationList() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);

  const publishUnreadCount = (rows) => {
    window.dispatchEvent(new CustomEvent('notifications:unread-count', {
      detail: rows.filter((notification) => !notification.is_read).length,
    }));
  };

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/notifications/');
      const rows = Array.isArray(response.data) ? response.data : response.data?.results;
      if (!Array.isArray(rows)) throw new Error('The notifications service returned an unexpected response.');
      const visibleRows = rows.filter((notification) => !isInternalDemoNotification(notification));
      setNotifications(visibleRows);
      publishUnreadCount(visibleRows);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Could not load notifications.');
    } finally {
      setLoading(false);
    }
  }, []);

  const markAsRead = async (notification) => {
    setUpdating(true);
    try {
      const response = await api.patch(`/notifications/${notification.id}/mark-read/`);
      const next = notifications.map((item) => item.id === notification.id ? response.data : item);
      setNotifications(next);
      publishUnreadCount(next);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Could not update notification.');
    } finally {
      setUpdating(false);
    }
  };

  const markAllAsRead = async () => {
    setUpdating(true);
    try {
      await api.patch('/notifications/mark-all-read/');
      const next = notifications.map((notification) => ({ ...notification, is_read: true }));
      setNotifications(next);
      publishUnreadCount(next);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Could not update notifications.');
    } finally {
      setUpdating(false);
    }
  };

  useEffect(() => {
    // Notification data is fetched asynchronously after the page mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadNotifications();
  }, [loadNotifications]);

  return (
    <section className="page-container notification-page" aria-labelledby="notifications-heading">
      <div className="page-header">
        <div><p className="eyebrow">Account updates</p><h1 id="notifications-heading">Notifications</h1></div>
        <div className="notification-actions">
          <button className="btn btn-secondary" onClick={markAllAsRead} disabled={loading || updating || !notifications.some((item) => !item.is_read)}>
            {updating ? 'Updating…' : 'Mark all as read'}
          </button>
          <button className="btn btn-secondary" onClick={loadNotifications} disabled={loading || updating}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>
      {loading && <p className="loading" role="status">Loading notifications…</p>}
      {!loading && error && (
        <div className="error" role="alert">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadNotifications}>Retry</button>
        </div>
      )}
      {!loading && !error && notifications.length === 0 && (
        <p className="empty-state" role="status">You have no notifications yet.</p>
      )}
      {!loading && !error && notifications.length > 0 && (
        <div className="notification-list">
          {notifications.map((notification) => (
            <article className={`notification-card ${notification.is_read ? 'read' : 'unread'}`} key={notification.id}>
              <div className="notification-card-heading">
                <h2>{displayText(notification.title)}</h2>
                <div className="notification-badges">
                  <span className={`read-badge ${notification.is_read ? 'read' : 'unread'}`}>{notification.is_read ? 'Read' : 'Unread'}</span>
                  <span className={`status-badge ${notification.status.toLowerCase()}`}>{notification.status}</span>
                </div>
              </div>
              <p>{displayText(notification.message)}</p>
              <footer>
                <span>{notification.type}</span>
                <time dateTime={notification.created_at}>{new Date(notification.created_at).toLocaleString()}</time>
                {!notification.is_read && <button className="notification-mark-read" disabled={updating} onClick={() => markAsRead(notification)}>Mark as read</button>}
              </footer>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default NotificationList;


