import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import { getApiError } from './eventManagement';

const initialForm = {
  title: '',
  message: '',
  type: 'PUSH',
  recipient_scope: 'ALL_CUSTOMERS',
  customer: '',
  event: '',
};

function AdminSendNotification() {
  const [options, setOptions] = useState({ customers: [], events: [] });
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadOptions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/notifications/send-options/');
      if (!Array.isArray(response.data?.customers) || !Array.isArray(response.data?.events)) {
        throw new Error('The notification recipients service returned an unexpected response.');
      }
      setOptions(response.data);
      setError('');
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load notification recipients.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load admin-only recipient choices when this page opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadOptions();
  }, [loadOptions]);

  const update = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setError('');
    setSuccess('');
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (form.recipient_scope === 'CUSTOMER' && !form.customer) {
      setError('Notification bhejne ke liye customer select karein.');
      return;
    }
    if (form.recipient_scope === 'EVENT_CUSTOMERS' && !form.event) {
      setError('Notification bhejne ke liye event select karein.');
      return;
    }

    const payload = {
      title: form.title.trim(),
      message: form.message.trim(),
      type: form.type,
      recipient_scope: form.recipient_scope,
    };
    if (form.recipient_scope === 'CUSTOMER') payload.customer = Number(form.customer);
    if (form.recipient_scope === 'EVENT_CUSTOMERS') payload.event = Number(form.event);

    setSending(true);
    try {
      const response = await api.post('/notifications/send/', payload);
      setSuccess(response.data?.message || `Notification ${response.data?.recipient_count || 0} customer inbox(es) mein save hui.`);
      setForm((current) => ({ ...current, title: '', message: '' }));
    } catch (requestError) {
      setError(getApiError(requestError, 'Notification save nahi ho saki.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="page-container management-page" aria-labelledby="send-notification-heading">
      <header className="page-header">
        <div><p className="eyebrow">Administrator workspace</p><h1 id="send-notification-heading">Send notification</h1></div>
      </header>
      <p>Customer ke in-app Notifications inbox mein update save karein.</p>
      <p className="notification-delivery-note" role="note">
        Notifications in-app hi save hongi. Email, SMS ya push service configured aur enabled nahi hai, isliye koi external message send nahi hoga.
      </p>

      {error && <div className="error" role="alert">{error}</div>}
      {!loading && error && options.customers.length === 0 && options.events.length === 0 && (
        <button className="btn btn-primary" type="button" onClick={loadOptions}>Try loading recipients again</button>
      )}
      {success && <p className="success-message" role="status">{success}</p>}
      {loading && <p className="loading" role="status">Recipients load ho rahe hain…</p>}

      {!loading && !error && (
        <form className="management-form" onSubmit={submit}>
          <div className="management-form-grid">
            <label>
              Notification title
              <input name="title" value={form.title} onChange={update} required maxLength="200" />
            </label>
            <label>
              Notification type
              <select name="type" value={form.type} onChange={update} required>
                <option value="PUSH">Push</option>
                <option value="EMAIL">Email</option>
                <option value="SMS">SMS</option>
              </select>
            </label>
            <label className="management-form-wide">
              Message
              <textarea name="message" value={form.message} onChange={update} required rows="5" />
            </label>
            <label>
              Recipients
              <select name="recipient_scope" value={form.recipient_scope} onChange={update} required>
                <option value="ALL_CUSTOMERS">All customers ({options.customers.length})</option>
                <option value="CUSTOMER">One specific customer</option>
                <option value="EVENT_CUSTOMERS">Customers with bookings for an event</option>
              </select>
            </label>
            {form.recipient_scope === 'CUSTOMER' && (
              <label>
                Customer
                <select name="customer" value={form.customer} onChange={update} required>
                  <option value="">Select a customer</option>
                  {options.customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>{customer.name} · {customer.email}</option>
                  ))}
                </select>
              </label>
            )}
            {form.recipient_scope === 'EVENT_CUSTOMERS' && (
              <label>
                Event
                <select name="event" value={form.event} onChange={update} required>
                  <option value="">Select an event</option>
                  {options.events.map((eventOption) => (
                    <option key={eventOption.id} value={eventOption.id}>
                      {eventOption.title} · {eventOption.event_date} · {eventOption.recipient_count} customers
                    </option>
                  ))}
                </select>
                {options.events.length === 0 && <small>Active booking wale events abhi available nahi hain.</small>}
              </label>
            )}
          </div>
          <div className="management-actions">
            <button className="btn btn-primary" type="submit" disabled={sending || (form.recipient_scope === 'ALL_CUSTOMERS' && options.customers.length === 0)}>
              {sending ? 'Saving notification…' : 'Send notification'}
            </button>
            <button className="btn btn-secondary" type="button" onClick={loadOptions} disabled={sending || loading}>Refresh recipients</button>
          </div>
        </form>
      )}
    </section>
  );
}

export default AdminSendNotification;
